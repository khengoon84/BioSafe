import sys
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(HERE/"src"))
from evidence_aware_subject_coverage_v0_2 import EvidenceAwareSubjectCoverageGuard


class EvidenceAwareCoverageTests(unittest.TestCase):
    def setUp(self):
        class Fallback:
            def apply(self,response,query,evidence):
                out=dict(response);out["conclusion"]="fallback";return out,[{"action":"fallback"}]
        self.guard=EvidenceAwareSubjectCoverageGuard(Fallback())
        self.evidence=[{"evidence_id":"CLM-036","claim_type":"risk_assessment_purpose","text":"Risk assessment supports risk management.","support_spans":[{"source_record_id":"S1"}],"source_sha256":"sha","verification_status":"SUPPORTED","evidence_origin":"C5_REVIEWED_CANDIDATE","candidate_path_id":"C37_METADATA_CFG02:metadata_off"}]

    def test_purpose_is_satisfied_by_structured_candidate_evidence(self):
        out,audit=self.guard.apply({"conclusion":"A risk assessment supports risk management."},"What is the purpose of a biosafety risk assessment?",self.evidence,{"retrieval_required":True})
        self.assertEqual(out["conclusion"],"A risk assessment supports risk management.")
        self.assertEqual(audit[0]["action"],"coverage_satisfied_by_structured_evidence")

    def test_empty_or_inadequate_provenance_delegates_to_fallback(self):
        evidence=[dict(self.evidence[0],support_spans=[])]
        out,audit=self.guard.apply({"conclusion":"A risk assessment supports risk management."},"What is the purpose of a biosafety risk assessment?",evidence,{"retrieval_required":True})
        self.assertEqual(out["conclusion"],"fallback");self.assertEqual(audit[0]["action"],"fallback")

    def test_project_specific_sufficiency_does_not_use_educational_shortcut(self):
        out,audit=self.guard.apply({"conclusion":"The assessment supports risk management."},"Is my biosafety risk assessment sufficient for me to start work?",self.evidence,{"retrieval_required":True})
        self.assertEqual(out["conclusion"],"fallback");self.assertEqual(audit[0]["action"],"fallback")


if __name__=="__main__":unittest.main()