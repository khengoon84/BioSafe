"""Deterministic tests for the C5-only authorization decision gate (cases A1-A8).

No Ollama call is required or permitted: the service-level tests fail the test
run if the model is invoked, proving the fail-closed short-circuit invariant.
"""
import json
import re
import sys
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE/"src"))
from authorization_gate_v0_1 import (
    AuthorizationIntent,
    evaluate_authorization_decision,
    decision_summary,
    load_vocabulary,
)

POSITIVE_PERMIT_PATTERN=re.compile(r"\b(?:biosafety permit|permit (?:level|levels) 1|level 1, 2|you need to obtain)\b",re.I)

A_CASES=[
    ("A1","What permit do I need?","AUTHORIZATION_APPLICABILITY",True,["jurisdiction","material_or_technology_trigger","specific_activity"],"REQUIRED"),
    ("A2","Is my project legal?","COMPLIANCE_STATUS",True,["jurisdiction","material_or_technology_trigger","specific_activity"],"REQUIRED"),
    ("A3","What approvals do I need?","AUTHORIZATION_APPLICABILITY",True,["jurisdiction","material_or_technology_trigger","specific_activity"],"REQUIRED"),
    ("A4","Can I start work now?","START_WORK_READINESS",True,["jurisdiction","material_or_technology_trigger","specific_activity"],"REQUIRED"),
    ("A5","What is a biosafety permit?","EDUCATIONAL",False,[],"OPTIONAL_EDUCATIONAL"),
    ("A6","Define biological risk group.","EDUCATIONAL",False,[],"OPTIONAL_EDUCATIONAL"),
    ("A7","What are the transport requirements for a clinical specimen in Malaysia?","AUTHORIZATION_APPLICABILITY",True,[],"REQUIRED"),
    ("A8","What does WHO say about risk assessment?","EDUCATIONAL",False,[],"OPTIONAL_EDUCATIONAL"),
]


class AuthorizationGateUnitTests(unittest.TestCase):
    def test_vocabulary_file_loads_and_validates(self):
        vocabulary=load_vocabulary()
        for key in ("high_stakes_terms","educational_terms","project_specific_markers","jurisdiction_terms","material_triggers","activity_verbs","authorization_claim_support_types"):
            self.assertTrue(vocabulary.get(key),f"vocabulary key missing or empty: {key}")

    def test_a1_through_a8_intent_and_readiness(self):
        for case_id,query,expected_intent,expected_high_stakes,expected_missing,expected_evidence in A_CASES:
            with self.subTest(case=case_id):
                decision=evaluate_authorization_decision(query)
                self.assertEqual(decision.intent.value,expected_intent)
                self.assertEqual(decision.high_stakes,expected_high_stakes)
                self.assertEqual(list(decision.missing_facts),expected_missing)
                self.assertEqual(decision.evidence_requirement,expected_evidence)
                if expected_high_stakes and expected_missing:
                    self.assertFalse(decision.positive_determination_allowed)
                    self.assertFalse(decision.negative_determination_allowed)
                    self.assertIn("INSUFFICIENT_FACTS",decision.reason_codes)
                    self.assertTrue(decision.retrieval_required)
                if not expected_high_stakes:
                    self.assertFalse(decision.jurisdiction_required)

    def test_a1_missing_facts_forbid_positive_and_negative_determinations(self):
        decision=evaluate_authorization_decision("What permit do I need?")
        self.assertFalse(decision.positive_determination_allowed)
        self.assertFalse(decision.negative_determination_allowed)

    def test_a7_facts_complete_requires_evidence_review(self):
        decision=evaluate_authorization_decision("What are the transport requirements for a clinical specimen in Malaysia?")
        self.assertEqual(decision.intent,AuthorizationIntent.AUTHORIZATION_APPLICABILITY)
        self.assertTrue(decision.retrieval_required)
        self.assertIn("EVIDENCE_REVIEW_REQUIRED",decision.reason_codes)

    def test_decision_summary_is_json_serializable(self):
        for _,query,_,_,_,_ in A_CASES:
            summary=decision_summary(evaluate_authorization_decision(query))
            round_trip=json.loads(json.dumps(summary))
            self.assertEqual(round_trip,summary)

    def test_gate_is_deterministic(self):
        first=decision_summary(evaluate_authorization_decision("What permit do I need?"))
        second=decision_summary(evaluate_authorization_decision("What permit do I need?"))
        self.assertEqual(first,second)

    def test_word_boundaries_prevent_false_jurisdiction_from_pronoun_like_tokens(self):
        decision=evaluate_authorization_decision("Tell me about whole blood handling.")
        self.assertEqual(decision.intent,AuthorizationIntent.NONE)
        self.assertFalse(decision.high_stakes)

    def test_empty_query_is_not_high_stakes(self):
        decision=evaluate_authorization_decision("   ")
        self.assertEqual(decision.intent,AuthorizationIntent.NONE)
        self.assertFalse(decision.high_stakes)


class ServiceFailClosedTests(unittest.TestCase):
    """Service-level invariant: GRD-02 fails closed BEFORE any model call."""

    @classmethod
    def setUpClass(cls):
        import full_inference_service_v0_1 as frozen
        from candidate_inference_service_v0_1 import CandidateInferenceServiceV01
        def forbidden(_model,_messages,_num_predict):
            raise AssertionError("Ollama was called for a fail-closed authorization query")
        cls._original=forbidden
        frozen._ollama=forbidden
        cls.service=CandidateInferenceServiceV01()

    @classmethod
    def tearDownClass(cls):
        import full_inference_service_v0_1 as frozen
        cls.service.close()

    def test_grd_02_fails_closed_without_model_call(self):
        response=self.service.infer({"query":"What permit do I need?"})
        gate=response["authorization_gate"]
        self.assertEqual(gate["intent"],"AUTHORIZATION_APPLICABILITY")
        self.assertTrue(gate["high_stakes"])
        self.assertFalse(gate["positive_determination_allowed"])
        self.assertEqual(gate["missing_facts"],["jurisdiction","material_or_technology_trigger","specific_activity"])
        self.assertIs(response["_meta"]["model_called"],False)
        self.assertEqual(response["safety"]["status"],"FAIL_CLOSED")
        self.assertEqual(response["authorization_assessment"]["status"],"INSUFFICIENT_FACTS")
        self.assertFalse(response["authorization_assessment"]["renderable"])
        self.assertIn("cannot determine",response["conclusion"].lower())
        self.assertFalse(POSITIVE_PERMIT_PATTERN.search(response["conclusion"]))
        self.assertTrue(response["missing_information"])
        round_trip=json.loads(json.dumps(response))
        self.assertEqual(round_trip["safety"]["status"],"FAIL_CLOSED")

    def test_fail_closed_response_is_deterministic(self):
        first=json.dumps(self.service.infer({"query":"What permit do I need?"}),sort_keys=True)
        second=json.dumps(self.service.infer({"query":"What permit do I need?"}),sort_keys=True)
        self.assertEqual(first,second)


class EndpointFailClosedTests(unittest.TestCase):
    """/api/ask integration: the gate guards the HTTP surface without Ollama."""

    @classmethod
    def setUpClass(cls):
        from candidate_service_v0_1 import app
        app.config["TESTING"]=True
        cls.client=app.test_client()
        import full_inference_service_v0_1 as frozen
        def forbidden(_model,_messages,_num_predict):
            raise AssertionError("Ollama was called for a fail-closed authorization query")
        cls._original=frozen._ollama
        frozen._ollama=forbidden

    @classmethod
    def tearDownClass(cls):
        import full_inference_service_v0_1 as frozen
        frozen._ollama=cls._original

    def test_ask_grd_02_fails_closed_over_http(self):
        response=self.client.post("/api/ask",json={"query":"What permit do I need?"})
        self.assertEqual(response.status_code,200)
        body=response.get_json()
        self.assertIs(body["_meta"]["model_called"],False)
        self.assertEqual(body["safety"]["status"],"FAIL_CLOSED")
        self.assertTrue(body["authorization_gate"]["missing_facts"])
        self.assertIn("cannot determine",body["conclusion"].lower())


if __name__=="__main__":unittest.main()
