import sys
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE/"src"))
from c5_bridge import ACTIVE_KB, ACTIVE_MANIFEST, digest, evaluate


class C5PreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=evaluate()

    def test_candidate_bridge_ready_but_live_blocked(self):
        self.assertEqual(self.report["result"],"READY_FOR_C5_DETERMINISTIC_SEMANTIC_STAGE")
        self.assertEqual(self.report["live_status"],"BLOCKED_UNTIL_C5_CANDIDATE_SERVICE_AND_ENVIRONMENT_PREFLIGHT")

    def test_candidate_identity_and_origin_are_explicit(self):
        self.assertEqual(self.report["candidate"],"C37_METADATA_CFG02:metadata_off")
        self.assertTrue(all(x["path_id"]==self.report["candidate"] for x in self.report["candidate_results"]))
        self.assertTrue(all(h["evidence_origin"]=="C5_REVIEWED_CANDIDATE" for x in self.report["candidate_results"] for h in x["evidence"]))
        self.assertTrue(all(h["source_sha256"] and h["verification_status"] for x in self.report["candidate_results"] for h in x["evidence"]))

    def test_frozen_hashes_and_claim_disposition(self):
        self.assertEqual(digest(ACTIVE_KB),"3d68f8154f6952a33395b253925ee44c2842a046c3c11d55f8c12ee9eb386bb4")
        self.assertEqual(digest(ACTIVE_MANIFEST),"199145afd64b1fb41f38921aba90ac214193f199dda4eb29f649c10eadf11031")
        self.assertEqual(len(self.report["claim_disposition"]["active_only_claim_ids"]),13)

    def test_activation_and_rollback_guards(self):
        self.assertEqual(self.report["claim_use_status"],"REVIEW_REQUIRED_BEFORE_CLAIM_USE")
        self.assertEqual(self.report["live_activation_status"],"PROHIBITED_PENDING_PHASE_C_GATES")
        self.assertTrue(self.report["rollback"]["automatic_reopen_on_failure"])


if __name__=="__main__":
    unittest.main()