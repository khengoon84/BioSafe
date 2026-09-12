import json
import sys
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE/"src"))
from authorization_contracts_v0_2 import FactStatus
from authorization_verifier_v0_2 import (
    FAIL_CLOSED_MESSAGE, apply_universal_authorization_verifier, load_ontology,
    verify_authorization_claims,
)


class AuthorizationVerifierTests(unittest.TestCase):
    CASE={"jurisdiction":{"value":"Malaysia","status":FactStatus.USER_ASSERTED.value},
          "material_or_technology_trigger":{"value":"LMO","status":"USER_ASSERTED"},
          "specific_activity":{"value":"contained use","status":"USER_ASSERTED"}}

    def test_canonical_ontology_loads_unknown_concepts_are_explicit(self):
        ontology=load_ontology()
        self.assertIn("REGISTRATION",ontology["authorization_concepts"])
        self.assertIn("CLEARANCE",ontology["authorization_concepts"])
        self.assertIn("forme",ontology["excluded_support_claim_types"])

    def test_unknown_regulatory_requirement_fails_closed(self):
        response={"conclusion":"You have to obtain a mandate from the department before starting work."}
        guarded,audit=apply_universal_authorization_verifier(response,[],self.CASE)
        self.assertEqual(guarded["conclusion"],FAIL_CLOSED_MESSAGE)
        self.assertEqual(guarded["authorization_assessment"]["status"],"UNKNOWN_REGULATORY_REQUIREMENT")
        self.assertEqual(audit[0]["action"],"withhold_unverified_authorization_claim")

    def test_known_clearance_without_evidence_fails_closed(self):
        result=verify_authorization_claims("You need to seek clearance from the biosafety committee.",[],self.CASE)
        self.assertEqual(result.status.value,"INSUFFICIENT_EVIDENCE")
        self.assertFalse(result.renderable)

    def test_unknown_intent_cannot_bypass_final_screen(self):
        response={"conclusion":"A certificate of registration is required for this activity."}
        guarded,audit=apply_universal_authorization_verifier(response,[],self.CASE)
        self.assertEqual(guarded["authorization_assessment"]["status"],"INSUFFICIENT_EVIDENCE")
        self.assertEqual(guarded["conclusion"],FAIL_CLOSED_MESSAGE)

    def test_query_like_unverified_facts_do_not_satisfy_contract(self):
        result=verify_authorization_claims(
            "You need a permit for LMO research in Malaysia.",[],
            {"jurisdiction":{"value":"Malaysia","status":"EXTRACTED_UNVERIFIED"},
             "material_or_technology_trigger":{"value":"LMO","status":"EXTRACTED_UNVERIFIED"},
             "specific_activity":{"value":"research","status":"EXTRACTED_UNVERIFIED"}})
        self.assertEqual(result.status.value,"INSUFFICIENT_FACTS")
        self.assertFalse(result.renderable)

    def test_supported_typed_claim_is_renderable(self):
        result=verify_authorization_claims(
            "A permit is required for this activity.",
            [{"evidence_id":"E1","claim_type":"permit_requirement"}],self.CASE)
        self.assertEqual(result.status.value,"VERIFIED")
        self.assertTrue(result.renderable)
        self.assertEqual(result.supported_evidence_ids,("E1",))

    def test_definitional_sentence_is_not_a_claim(self):
        guarded,audit=apply_universal_authorization_verifier(
            {"conclusion":"A permit is a legal instrument that authorizes an activity."},[],self.CASE)
        self.assertEqual(guarded["conclusion"],"A permit is a legal instrument that authorizes an activity.")
        self.assertEqual(audit,[])
        self.assertEqual(guarded["authorization_assessment"]["status"],"NO_CLAIM")

    def test_conflicting_or_missing_facts_fail_closed(self):
        result=verify_authorization_claims("A permit is required for this activity.",[],
            {"jurisdiction":{"value":"Malaysia","status":"CONFLICTING"},
             "material_or_technology_trigger":{"value":"LMO","status":"USER_ASSERTED"},
             "specific_activity":{"value":"research","status":"USER_ASSERTED"}})
        self.assertEqual(result.status.value,"INSUFFICIENT_FACTS")

    def test_json_round_trip(self):
        guarded,_=apply_universal_authorization_verifier(
            {"conclusion":"You need to seek clearance from the biosafety committee."},[],self.CASE)
        json.dumps(guarded)

    def test_candidate_service_applies_verifier_when_input_intent_is_none(self):
        from candidate_inference_service_v0_1 import CandidateInferenceServiceV01
        service=CandidateInferenceServiceV01()
        try:
            service.service.infer=lambda prepared, documents=None: {
                "conclusion":"You have to obtain a mandate from the department before starting work.",
                "evidence":[],
            }
            guarded=service.infer({"query":"Explain a general biosafety concept."})
            self.assertEqual(guarded["authorization_assessment"]["status"],
                             "UNKNOWN_REGULATORY_REQUIREMENT")
            self.assertEqual(guarded["conclusion"],FAIL_CLOSED_MESSAGE)
        finally:
            service.close()


if __name__=="__main__":
    unittest.main()