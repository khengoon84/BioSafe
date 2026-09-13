import json
import sys
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(HERE/"src"))
from phase4_ab import evaluate, EXPECTED, ACTIVE_KB, ACTIVE_MANIFEST, digest

class Phase4Tests(unittest.TestCase):
    def test_readiness_is_not_activation(self):
        report=evaluate();self.assertEqual(report["result"],"READY_FOR_C5_SEMANTIC_LIVE_ACCEPTANCE")
        self.assertEqual(report["live_activation_status"],"PROHIBITED_PENDING_PHASE_C_GATES")
        self.assertEqual(report["claim_use_status"],"REVIEW_REQUIRED_BEFORE_CLAIM_USE")

    def test_selected_candidate_and_control_hashes(self):
        report=evaluate();self.assertEqual(report["candidate"],"C37_METADATA_CFG02:metadata_off")
        self.assertEqual(digest(ACTIVE_KB),EXPECTED["kb"]);self.assertEqual(digest(ACTIVE_MANIFEST),EXPECTED["manifest"])

    def test_synthetic_fixture_is_excluded_and_rollback_exists(self):
        report=evaluate();self.assertTrue(report["synthetic_fixture_excluded"]);self.assertEqual(report["rollback"]["status"],"AVAILABLE");self.assertTrue(report["rollback"]["automatic_reopen_on_failure"])

if __name__=="__main__": unittest.main()