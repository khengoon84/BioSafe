import json
import sys
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE/"src"))
from authorization_evidence_readiness_v0_1 import evaluate_evidence_readiness
from authorization_verifier_v0_2 import load_ontology


class AuthorizationEvidenceReadinessTests(unittest.TestCase):
    def setUp(self):
        self.ontology=load_ontology()

    def test_current_kb_has_no_reviewed_authorization_claims(self):
        root=HERE.parent
        kb=json.loads((root/"data/BioSafe_Knowledge_Base_v0.2.json").read_text())
        report=evaluate_evidence_readiness(kb["claims"],self.ontology)
        self.assertEqual(report["authorization_claim_count"],0)
        self.assertEqual(report["result"],"NO_REVIEWED_AUTHORIZATION_CLAIMS")
        self.assertFalse(report["positive_claims_renderable"])
        self.assertFalse(report["negative_claims_renderable"])

    def test_incomplete_authorization_record_is_not_ready(self):
        report=evaluate_evidence_readiness([{"claim_type":"permit_requirement"}],self.ontology)
        self.assertEqual(report["authorization_claim_count"],1)
        self.assertEqual(report["metadata_complete_count"],0)
        self.assertGreater(report["missing_required_metadata"]["jurisdiction"],0)
        self.assertEqual(report["result"],"NO_REVIEWED_AUTHORIZATION_CLAIMS")

    def test_complete_record_is_ready_for_review_not_automatic_use(self):
        record={"evidence_id":"E1","claim_type":"permit_requirement","jurisdiction":"Malaysia",
                "material_or_technology_trigger":"LMO","specific_activity":"contained use",
                "authority_status":"verified","currentness":"current","polarity":"REQUIRED",
                "normative_force":"required"}
        report=evaluate_evidence_readiness([record],self.ontology)
        self.assertEqual(report["metadata_complete_count"],1)
        self.assertEqual(report["result"],"READY_FOR_REVIEWED_AUTHORIZATION_CLAIMS")
        self.assertFalse(report["positive_claims_renderable"])

    def test_form_e_is_not_authorization_evidence(self):
        report=evaluate_evidence_readiness([{"claim_type":"forme"}],self.ontology)
        self.assertEqual(report["authorization_claim_count"],0)


if __name__=="__main__":
    unittest.main()