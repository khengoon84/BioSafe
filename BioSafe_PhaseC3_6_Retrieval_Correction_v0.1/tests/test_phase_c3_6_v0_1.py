import sys, unittest
from pathlib import Path
HERE=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(HERE/"src")); sys.path.insert(0,str(HERE/"scripts"))
from phase_c3_6 import evaluate, artifacts

class C36Tests(unittest.TestCase):
    def test_independent_catalog_is_two_queries_per_claim(self):
        _,gold=artifacts(); rows=gold["cases"]; ind=[x for x in rows if x["case_type"]=="independent_claim"]
        self.assertEqual(len(ind),64); self.assertEqual(len({x["query"] for x in ind}),64)
    def test_unknown_cases_exist(self):
        _,gold=artifacts(); self.assertGreaterEqual(sum(x["case_type"]=="unknown_evidence" for x in gold["cases"]),3)
    def test_report_remains_blocked(self):
        self.assertEqual(evaluate()["gate_result"],"BLOCKED_PENDING_OWNER_REVIEW")
    def test_activation_status_preserved(self):
        self.assertEqual(artifacts()[0]["live_activation_status"],"PROHIBITED_PENDING_PHASE_C_GATES")

    def test_fixture_hash_chain_is_consistent(self):
        import hashlib, json
        p=HERE/"fixtures"; source=hashlib.sha256((p/"source.txt").read_bytes()).hexdigest()
        for name in ("source_policy_extension.json","component_map_extension.json","crosswalk_extension.json"):
            self.assertEqual(json.loads((p/name).read_text())["source_sha256"],source)

    def test_unknown_evidence_fails_closed(self):
        report=evaluate()
        for mode in report["cases"].values():
            for row in mode["metadata_on"]:
                if row["case_type"] == "unknown_evidence":
                    self.assertEqual(row["ranked_claim_ids"], [])

    def test_metadata_on_is_a_real_candidate_path(self):
        report=evaluate()
        for mode in report["cases"].values():
            on=mode["metadata_on"]; off=mode["metadata_off"]
            self.assertTrue(any(row["metadata_score_present"] for row in on))
            self.assertTrue(all(not row["metadata_score_present"] for row in off))

if __name__=="__main__": unittest.main()