import json, sys, unittest
from pathlib import Path
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "src")); sys.path.insert(0, str(HERE / "scripts"))
from phase_c3_4 import build_artifacts, evaluate, policy_valid
from build_retrieval_policy import build_artifact


class C34Tests(unittest.TestCase):
    def test_policy_covers_reviewed_documents_and_status(self):
        self.assertTrue(policy_valid(build_artifact()))
        self.assertEqual(len(build_artifact()["documents"]), 17)

    def test_artifacts_are_deterministic(self):
        a = build_artifact(); b = build_artifact(); self.assertEqual(a, b)

    def test_report_is_review_blocked_and_fixture_passes(self):
        report = evaluate()
        self.assertEqual(report["gate_result"], "BLOCKED_PENDING_OWNER_REVIEW")
        for summary in report["summary"].values():
            self.assertEqual(summary["new_document_recall_at_10"], 1)

    def test_no_live_status_change(self):
        policy = build_artifact()
        self.assertEqual(policy["live_activation_status"], "PROHIBITED_PENDING_PHASE_C_GATES")


if __name__ == "__main__":
    unittest.main()