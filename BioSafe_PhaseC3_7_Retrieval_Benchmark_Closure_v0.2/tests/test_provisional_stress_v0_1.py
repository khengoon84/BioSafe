import sys
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(HERE/"src"),str(HERE/"scripts")]
from provisional_stress import evaluate, owner_review_packet


class ProvisionalStressTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=evaluate(); cls.packet=owner_review_packet(cls.report)

    def test_provisional_result_can_never_close_c3(self):
        self.assertEqual(self.report["benchmark_mode"],"PROVISIONAL_NON_INDEPENDENT_NOT_A_C3_CLOSURE_GATE")
        self.assertEqual(self.report["gate_result"],"BLOCKED_INDEPENDENT_HOLDOUT_AND_OWNER_REVIEW")
        self.assertNotIn(self.report["provisional_result"],{"PASS","PASS_PENDING_OWNER_REVIEW"})

    def test_predeclared_candidate_and_input_hash_are_recorded(self):
        self.assertEqual(self.report["candidate"],"C37_METADATA_CFG02:metadata_off")
        self.assertEqual(len(self.report["input_hashes"]["stress_cases"]),64)

    def test_all_provisional_machine_gates_pass(self):
        self.assertEqual(self.report["provisional_result"],"PROVISIONAL_PASS_NOT_GATE_ELIGIBLE")
        self.assertTrue(all(self.report["summary"]["hard_gates"].values()))
        self.assertEqual(self.report["summary"]["recall_at_10"],1.0)

    def test_owner_packet_records_only_the_provided_overall_decision(self):
        self.assertEqual(self.packet["review_scope"],"PROVISIONAL_STRESS_RESULTS_NOT_C3_APPROVAL")
        self.assertEqual(self.packet["reviewer_identity"],"BioSafe project owner")
        self.assertEqual(self.packet["overall_disposition"],"ACCEPT_PROVISIONAL_RESULT")
        self.assertEqual(self.packet["granular_case_attestations"],"NOT_PROVIDED_REMAIN_UNSET")
        self.assertTrue(all(row["owner_disposition"] is None for row in self.packet["cases"]))
        self.assertTrue(all(row["expected_contract"]["query"] for row in self.packet["cases"]))
        self.assertTrue(all(row["retrieved_acceptable_evidence"] or row["expected_contract"]["retrieval_must_be_empty"] for row in self.packet["cases"]))

    def test_acceptance_does_not_change_safety_or_gate_status(self):
        self.assertEqual(self.report["gate_result"],"BLOCKED_INDEPENDENT_HOLDOUT_AND_OWNER_REVIEW")
        self.assertEqual(self.packet["claim_use_status"],"REVIEW_REQUIRED_BEFORE_CLAIM_USE")
        self.assertEqual(self.packet["live_activation_status"],"PROHIBITED_PENDING_PHASE_C_GATES")
        self.assertTrue(self.packet["scope_acknowledgements"]["independent_holdout_still_required"])


if __name__=="__main__": unittest.main()