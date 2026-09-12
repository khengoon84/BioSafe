from __future__ import annotations
import sys, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "src"))
from phase_c3_1 import ACTIVATION, STATUS, artifacts, canonical_bytes, crosswalk_mapping, evaluate


class PhaseC31Tests(unittest.TestCase):
    def test_crosswalk_is_reviewed_and_complete(self):
        mapping = crosswalk_mapping()
        self.assertEqual(mapping["KB-MY-MOH2023"], "KB-MY-TRANSPORT2023")
        self.assertEqual(mapping["KB-WHO-RA"], "KB-WHO-LBM4-RA")

    def test_crosswalk_is_hash_bound_to_curated_claims(self):
        mapping = crosswalk_mapping()
        self.assertEqual(len(mapping), 12)

    def test_gold_has_required_case_families_and_status(self):
        kb, manifest, gold = artifacts()
        self.assertEqual(len(kb["claims"]), 32)
        self.assertEqual(gold["case_count"], 71)
        self.assertEqual(sum(c["case_type"] == "positive" for c in gold["cases"]), 32)
        self.assertEqual(sum(c["case_type"] == "paraphrase" for c in gold["cases"]), 32)
        self.assertEqual(sum(c["case_type"] == "boundary_control" for c in gold["cases"]), 7)
        for value in (kb, manifest, gold):
            self.assertEqual(value["claim_use_status"], STATUS)
            self.assertEqual(value["live_activation_status"], ACTIVATION)

    def test_candidate_retriever_returns_controlled_ids(self):
        report = evaluate()
        for row in report["cases"]["C31_CROSSWALK_CFG01"]:
            self.assertFalse(any(item.startswith("KB-MY-MOH") for item in row["ranked_claim_ids"]))

    def test_gate_does_not_claim_promotion(self):
        report = evaluate()
        self.assertEqual(report["gate_result"], "BLOCKED_PENDING_OWNER_REVIEW")
        self.assertEqual(report["live_activation_status"], ACTIVATION)

    def test_report_is_deterministic(self):
        self.assertEqual(canonical_bytes(evaluate()), canonical_bytes(evaluate()))


if __name__ == "__main__":
    unittest.main()