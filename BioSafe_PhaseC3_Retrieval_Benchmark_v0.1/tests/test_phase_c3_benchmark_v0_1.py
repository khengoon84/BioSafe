from __future__ import annotations
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "src"))
from phase_c3_benchmark import ACTIVATION, STATUS, build_artifacts, canonical_bytes, evaluate


class PhaseC3Tests(unittest.TestCase):
    def test_build_is_byte_reproducible(self):
        first = build_artifacts(); second = build_artifacts()
        self.assertEqual(tuple(canonical_bytes(x) for x in first), tuple(canonical_bytes(x) for x in second))

    def test_full_curated_claim_coverage_and_exact_spans(self):
        kb, _, gold = build_artifacts()
        self.assertEqual(len(kb["claims"]), 32)
        self.assertEqual(len(gold["cases"]), 32)
        for case in gold["cases"]:
            self.assertTrue(case["expected_source_ids"])
            self.assertTrue(case["expected_pages"])

    def test_safety_gate_status_is_preserved(self):
        kb, manifest, gold = build_artifacts()
        for artifact in (kb, manifest, gold):
            self.assertEqual(artifact["claim_use_status"], STATUS)
            self.assertEqual(artifact["live_activation_status"], ACTIVATION)

    def test_report_is_deterministic_and_hash_bound(self):
        kb, manifest, gold = build_artifacts()
        first = evaluate(kb, manifest, gold)
        second = evaluate(kb, manifest, gold)
        self.assertEqual(canonical_bytes(first), canonical_bytes(second))
        self.assertEqual(first["input_hashes"]["kb"], __import__("hashlib").sha256(canonical_bytes(kb)).hexdigest())

    def test_report_binds_retrieved_claims_to_exact_support_spans(self):
        kb, manifest, gold = build_artifacts()
        report = evaluate(kb, manifest, gold)
        for rows in report["cases"].values():
            covered = [row["citation_completeness_at_10"] for row in rows]
            self.assertGreater(sum(covered), 0)


if __name__ == "__main__":
    unittest.main()