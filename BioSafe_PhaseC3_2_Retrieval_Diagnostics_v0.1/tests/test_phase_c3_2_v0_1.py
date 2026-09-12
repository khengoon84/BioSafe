from __future__ import annotations
import sys, unittest
from pathlib import Path
HERE=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(HERE/"src"))
from phase_c3_2 import ACTIVATION, STATUS, artifacts, canonical_bytes, evaluate, reviewed_crosswalk

class PhaseC32Tests(unittest.TestCase):
    def test_dynamic_reviewed_crosswalk(self):
        m=reviewed_crosswalk(); self.assertEqual(m["KB-MY-MOH2023"],"KB-MY-TRANSPORT2023"); self.assertEqual(len(m),12)
    def test_unique_paraphrases_and_boundary_oracles(self):
        _,_,g=artifacts(); self.assertEqual(g["case_count"],71); self.assertEqual(len({c["query"] for c in g["cases"]}),71)
        b=[c for c in g["cases"] if c["case_type"]=="boundary_control"]; self.assertTrue(all(c["forbidden_document_ids"] for c in b)); self.assertTrue(all("forbidden_claim_ids" in c for c in b))
    def test_status_and_gate_are_preserved(self):
        report=evaluate(); self.assertEqual(report["gate_result"],"BLOCKED_PENDING_OWNER_REVIEW"); self.assertEqual(report["claim_use_status"],STATUS); self.assertEqual(report["live_activation_status"],ACTIVATION)
    def test_boundary_report_checks_documents(self):
        report=evaluate()
        for rows in report["cases"].values():
            self.assertTrue(all("forbidden_documents_top3" in row for row in rows))

    def test_report_scores_exact_support_spans(self):
        report=evaluate()
        for rows in report["cases"].values():
            self.assertTrue(all("support_span_completeness_at_10" in row for row in rows))
        self.assertGreater(report["summary"]["C32_CROSSWALK_CFG02"]["mean_support_span_completeness_at_10"], 0)
    def test_deterministic_report(self):
        self.assertEqual(canonical_bytes(evaluate()),canonical_bytes(evaluate()))

if __name__=="__main__": unittest.main()