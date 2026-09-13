import hashlib
import json
import sys
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(HERE/"src"),str(HERE/"scripts")]
from contracts import BenchmarkCase
from phase_c3_7 import C37CFG01, artifacts, build_artifacts, cases, evaluate, retrieval_policy, validate_cases, _fixture


class C37V02Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=evaluate()

    def test_artifact_is_valid_and_statuses_remain_guarded(self):
        self.assertEqual(self.report["artifact_validation_errors"],[])
        self.assertEqual(self.report["machine_gate_result"],"BLOCKED_HOLDOUT_AND_OWNER_REVIEW")
        self.assertEqual(self.report["gate_result"],"BLOCKED_PENDING_OWNER_REVIEW")
        self.assertEqual(self.report["claim_use_status"],"REVIEW_REQUIRED_BEFORE_CLAIM_USE")
        self.assertEqual(self.report["live_activation_status"],"PROHIBITED_PENDING_PHASE_C_GATES")

    def test_catalog_has_baseline_case_classes_and_seven_boundaries(self):
        _,gold=artifacts(); rows=gold["cases"]
        self.assertEqual(len({r["case_id"] for r in rows}),len(rows))
        self.assertEqual(len({r["query"] for r in rows}),len(rows))
        self.assertTrue({"independent_claim","unknown_evidence","boundary","minimal_pair","conflict","currentness"}<={r["case_type"] for r in rows})
        self.assertEqual(sum(r["case_type"]=="boundary" for r in rows),7)

    def test_who_acronym_is_not_interrogative_who(self):
        classifier=object.__new__(C37CFG01)
        self.assertEqual(classifier.classify("Who completes the IBC Assessment Report?").jurisdiction,"Malaysia")
        self.assertEqual(classifier.classify("What does WHO say about risk assessment?").jurisdiction,"International")

    def test_unknown_currentness_and_conflict_cases_fail_closed(self):
        for modes in self.report["cases"].values():
            for row in modes["metadata_off"]:
                if row["case_type"] in {"unknown_evidence","currentness","conflict"}:
                    self.assertEqual(row["ranked_claim_ids"],[])
                    self.assertTrue(row["unknown_fail_closed"] or row["currentness_ok"] or row["conflict_ok"])

    def test_boundaries_are_conjunctive_and_provenance_is_complete(self):
        for modes in self.report["cases"].values():
            for row in modes["metadata_off"]:
                if row["case_type"]=="boundary":
                    self.assertTrue(row["retrieval_ok"])
                    self.assertTrue(row["boundary_preserved"])
                if row["retrieval_ok"] and row["support_span_status"]!="NOT_APPLICABLE":
                    self.assertEqual(row["support_span_status"],"COMPLETE")

    def test_cfg02_metadata_off_is_only_eligible_development_candidate(self):
        self.assertEqual(self.report["eligible_development_candidates"],["C37_METADATA_CFG02:metadata_off"])
        self.assertEqual(self.report["summary"]["C37_METADATA_CFG02"]["metadata_off"]["independent_recall_at_10"],1.0)
        self.assertFalse(self.report["summary"]["C37_METADATA_CFG02"]["metadata_on_candidate_eligible"])
        self.assertTrue(self.report["summary"]["C37_METADATA_CFG02"]["metadata_comparison"]["rank_harmed_case_ids"])

    def test_invalid_case_contract_fails_validation(self):
        kb,_,_=build_artifacts(); policy=retrieval_policy(); fkb,fpol,_=_fixture(kb,policy)
        bad=BenchmarkCase.from_dict({"case_id":"BAD","case_type":"positive","query":"x","acceptable_claim_ids":[],"metrics":["retrieval"]})
        self.assertTrue(validate_cases([bad],fkb,fpol))

    def test_summary_gates_all_evidence_bearing_cases(self):
        for variant in self.report["summary"].values():
            for mode in ("metadata_on","metadata_off"):
                self.assertIn("all_evidence_case_coverage",variant[mode]["hard_gates"])

    def test_fixture_hash_chain_is_consistent(self):
        digest=hashlib.sha256((HERE/"fixtures/source.txt").read_bytes()).hexdigest()
        for name in ("source_policy_extension.json","component_map_extension.json","crosswalk_extension.json"):
            self.assertEqual(json.loads((HERE/"fixtures"/name).read_text())["source_sha256"],digest)


if __name__=="__main__": unittest.main()