from __future__ import annotations
import sys,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(HERE/"src"))
from phase_c3_3 import ACTIVATION,STATUS,artifacts,canonical_bytes,evaluate,reviewed_crosswalk
class PhaseC33Tests(unittest.TestCase):
 def test_case_contract_is_corrected(self):
  _,_,g=artifacts(); self.assertEqual(g["case_count"],75); self.assertEqual(len({x["query"] for x in g["cases"]}),75)
  b=[x for x in g["cases"] if x["case_type"]=="semantic_boundary"]; self.assertTrue(all("required_boundary" in x for x in b)); self.assertTrue(all(not x["retrieval_must_be_empty"] for x in b))
 def test_crosswalk_and_status(self):
  self.assertEqual(len(reviewed_crosswalk()),12); r=evaluate(); self.assertEqual(r["claim_use_status"],STATUS); self.assertEqual(r["live_activation_status"],ACTIVATION)
 def test_boundary_report_has_semantic_fields(self):
  r=evaluate(); self.assertTrue(all("boundary_evidence_available" in x for rows in r["cases"].values() for x in rows if x["case_type"]=="semantic_boundary"))
 def test_determinism(self): self.assertEqual(canonical_bytes(evaluate()),canonical_bytes(evaluate()))
if __name__=="__main__": unittest.main()