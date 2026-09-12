import sys, unittest
from pathlib import Path
HERE=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(HERE/"src")); sys.path.insert(0,str(HERE/"scripts"))
from phase_c3_5 import evaluate, artifacts

class C35Tests(unittest.TestCase):
    def test_independent_catalog_is_two_queries_per_claim(self):
        _,gold=artifacts(); rows=gold["cases"]; ind=[x for x in rows if x["case_type"]=="independent_claim"]
        self.assertEqual(len(ind),64); self.assertEqual(len({x["query"] for x in ind}),64)
    def test_unknown_cases_exist(self):
        _,gold=artifacts(); self.assertGreaterEqual(sum(x["case_type"]=="unknown_evidence" for x in gold["cases"]),3)
    def test_report_remains_blocked(self):
        self.assertEqual(evaluate()["gate_result"],"BLOCKED_PENDING_OWNER_REVIEW")
    def test_activation_status_preserved(self):
        self.assertEqual(artifacts()[0]["live_activation_status"],"PROHIBITED_PENDING_PHASE_C_GATES")

if __name__=="__main__": unittest.main()