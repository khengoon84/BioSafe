import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "unified_v1/src"))

from biosafe_unified2251.guards import DecisionSemanticsGuard, vetted_direct_answer
from biosafe_unified2241 import EvidencePreservingSemanticVerifier


def apply(text, query, case_state=None, evidence=None):
    response = {
        "conclusion": text,
        "missing_information": [],
        "safety": {"classification": "normal", "response_mode": "answer"},
    }
    return DecisionSemanticsGuard().apply(
        response, query, case_state or {}, evidence or []
    )[0]


class SemanticGateTests(unittest.TestCase):
    def test_unknown_permit_is_not_negative_determination(self):
        out = apply("No specific permit is required for this query.", "What permit do I need?")
        self.assertIn("insufficient to determine", out["conclusion"].lower())
        self.assertNotIn("no specific permit", out["conclusion"].lower())
        self.assertEqual(out["safety"]["response_mode"], "ask_before_concluding")

    def test_unknown_law_is_not_declared_nonexistent(self):
        out = apply(
            "The Imaginary Biosecurity Act 2042 does not exist.",
            "What does the Imaginary Biosecurity Act 2042 require?",
        )
        self.assertIn("could not verify", out["conclusion"].lower())
        self.assertNotIn("does not exist", out["conclusion"].lower())

    def test_compliance_verdict_is_replaced(self):
        out = apply("Your project is not legally compliant.", "Is my project legal?")
        self.assertIn("cannot determine or certify", out["conclusion"].lower())
        self.assertNotIn("not legally compliant", out["conclusion"].lower())

    def test_qualified_compliance_verdict_is_replaced(self):
        out = apply("Your project is not yet legally compliant.", "Is my project legal?")
        self.assertIn("cannot determine or certify", out["conclusion"].lower())
        self.assertNotIn("not yet legally compliant", out["conclusion"].lower())

    def test_form_e_is_not_a_permit(self):
        out = apply(
            "You cannot start work without obtaining a Biosafety Permit (Form E).",
            "Can I start work now?",
        )
        low = out["conclusion"].lower()
        self.assertIn("cannot authorize", low)
        self.assertNotIn("biosafety permit", low)

    def test_unsupported_section_is_removed(self):
        out = apply(
            "Section 37 requires a completed IBC Assessment Report.",
            "Is my project legal?",
            evidence=[{"evidence_id": "CLM-025", "text": "The IBC completes its assessment report."}],
        )
        self.assertNotIn("section 37", out["conclusion"].lower())

    def test_explicit_trigger_state_can_preserve_supported_mandate(self):
        out = apply(
            "You need to submit a notification.",
            "What notification applies?",
            case_state={
                "jurisdiction": "Malaysia",
                "is_lmo": True,
                "regulated_activity": "contained use",
            },
            evidence=[{"text": "A notification is required for this specified activity."}],
        )
        self.assertEqual(out["conclusion"], "You need to submit a notification.")

    def test_trigger_state_does_not_rescue_unrelated_evidence(self):
        out = apply(
            "You need to submit a notification.",
            "What notification applies?",
            case_state={
                "jurisdiction": "Malaysia",
                "is_lmo": True,
                "regulated_activity": "contained use",
            },
            evidence=[{"text": "The committee monitors training and facilities."}],
        )
        self.assertIn("insufficient to determine", out["conclusion"].lower())

    def test_mandate_with_unsupported_provision_is_removed(self):
        response = {
            "conclusion": "The available information is insufficient to determine what applies.",
            "recommended_next_step": [
                "Submit the notification under Regulation 16 of the applicable regulations."
            ],
        }
        out, audit = DecisionSemanticsGuard().apply(
            response, "What approvals do I need?", {}, []
        )
        recommendation = " ".join(out["recommended_next_step"]).lower()
        self.assertNotIn("submit the notification", recommendation)
        self.assertNotIn("regulation 16", recommendation)
        self.assertTrue(
            any(
                item.get("field") == "recommended_next_step"
                and item.get("action") == "remove_unsupported_exact_provision"
                for item in audit
            )
        )

    def test_unsupported_provision_is_removed_from_recommendations(self):
        response = {
            "conclusion": "BioSafe cannot determine the applicable process.",
            "recommendations": [
                "Consult your institutional biosafety office.",
                "Submit an application under Section 37.",
            ],
        }
        out, audit = DecisionSemanticsGuard().apply(
            response, "What approvals do I need?", {}, []
        )
        self.assertEqual(
            out["recommendations"], ["Consult your institutional biosafety office."]
        )
        self.assertTrue(
            any(
                item.get("field") == "recommendations"
                and item.get("action") == "remove_unsupported_exact_provision"
                for item in audit
            )
        )

    def test_untriggered_submit_for_approval_is_replaced(self):
        response = {
            "conclusion": "The available information is insufficient to determine what applies.",
            "recommended_next_step": [
                "Submit the IBC Assessment Report to the Department of Biosafety for approval."
            ],
        }
        out, _ = DecisionSemanticsGuard().apply(
            response, "Is my project legal?", {}, []
        )
        recommendation = " ".join(out["recommended_next_step"]).lower()
        self.assertNotIn("submit the ibc assessment report", recommendation)
        self.assertNotIn("for approval", recommendation)
        self.assertIn("confirm", recommendation)

    def test_untriggered_submission_to_authority_is_replaced(self):
        response = {
            "conclusion": "BioSafe cannot determine the applicable process.",
            "recommended_next_step": [
                "Submit the completed IBC Assessment Report to the Department of Biosafety."
            ],
        }
        out, _ = DecisionSemanticsGuard().apply(
            response, "Is my project legal?", {}, []
        )
        recommendation = " ".join(out["recommended_next_step"]).lower()
        self.assertNotIn("submit the completed ibc assessment report", recommendation)
        self.assertIn("confirm", recommendation)

    def test_untriggered_document_submission_imperative_is_replaced(self):
        response = {
            "conclusion": "BioSafe cannot determine the applicable process.",
            "recommended_next_step": [
                "Submit the IBC Assessment Report as evidence to confirm that the "
                "project scope is within acceptable boundaries."
            ],
        }
        out, audit = DecisionSemanticsGuard().apply(
            response, "Is my project legal?", {}, []
        )
        recommendation = " ".join(out["recommended_next_step"]).lower()
        self.assertNotIn("submit the ibc assessment report", recommendation)
        self.assertIn("confirm", recommendation)
        self.assertTrue(
            any(
                item.get("action") == "downgrade_untriggered_authorization"
                for item in audit
            )
        )

    def test_untriggered_submission_directive_in_missing_information_is_replaced(self):
        response = {
            "conclusion": "BioSafe cannot determine the applicable process.",
            "missing_information": [
                "Submit the IBC Assessment Report as evidence to confirm that the "
                "project scope is within acceptable boundaries."
            ],
        }
        out, audit = DecisionSemanticsGuard().apply(
            response, "Is my project legal?", {}, []
        )
        text = " ".join(out["missing_information"]).lower()
        self.assertNotIn("submit the ibc assessment report", text)
        self.assertIn("confirm", text)
        self.assertTrue(
            any(item.get("field") == "missing_information" for item in audit)
        )

    def test_form_e_is_not_represented_as_a_risk_assessment_plan(self):
        response = {
            "conclusion": "BioSafe cannot determine the applicable process.",
            "recommended_next_step": [
                "Request a formal risk assessment plan (Form E) detailing safety procedures."
            ],
        }
        out, audit = DecisionSemanticsGuard().apply(
            response, "Is my project legal?", {}, []
        )
        recommendation = " ".join(out["recommended_next_step"]).lower()
        self.assertNotIn("risk assessment plan (form e)", recommendation)
        self.assertIn("cannot treat form e", recommendation)
        self.assertTrue(
            any(item.get("action") == "replace_form_e_mischaracterization" for item in audit)
        )

    def test_safe_recommendation_is_preserved(self):
        response = {
            "conclusion": "More facts are needed.",
            "recommended_next_step": [
                "Consult your institutional biosafety office for case-specific review."
            ],
        }
        out, _ = DecisionSemanticsGuard().apply(
            response, "What approvals do I need?", {}, []
        )
        self.assertEqual(out["recommended_next_step"], response["recommended_next_step"])

    def test_supported_recommendation_mandate_is_preserved(self):
        response = {
            "conclusion": "The scoped evidence supports a notification requirement.",
            "recommended_next_step": ["Submit the notification."],
        }
        out, _ = DecisionSemanticsGuard().apply(
            response,
            "What notification applies?",
            {
                "jurisdiction": "Malaysia",
                "is_lmo": True,
                "regulated_activity": "contained use",
            },
            [{"text": "A notification is required for this specified activity."}],
        )
        self.assertEqual(out["recommended_next_step"], ["Submit the notification."])

    def test_vetted_general_answers_are_non_determinative(self):
        biosafety = vetted_direct_answer("What is biosafety?")["direct_answer"].lower()
        risk_group = vetted_direct_answer("What is a biological risk group?")["direct_answer"].lower()
        acronyms = vetted_direct_answer("What is PI and IBC?")["direct_answer"].lower()
        self.assertIn("accidental release", biosafety)
        self.assertIn("does not by itself determine", risk_group)
        self.assertIn("principal investigator", acronyms)
        self.assertIn("institutional biosafety committee", acronyms)




class SemanticVerifierNegationTests(unittest.TestCase):
    """Negated predicates (e.g., 'cannot certify') are limitations, not claims, and must be preserved."""

    def test_negated_certify_is_preserved(self):
        response = {"conclusion": "BioSafe cannot certify compliance without explicit data."}
        out, audit = EvidencePreservingSemanticVerifier().apply(response, [])
        self.assertIn("cannot certify", out["conclusion"].lower())
        self.assertFalse(any(item.get("action") == "remove" for item in audit))

    def test_negated_approve_is_preserved(self):
        response = {"conclusion": "The Board cannot approve this without further review."}
        out, _ = EvidencePreservingSemanticVerifier().apply(response, [])
        self.assertIn("cannot approve", out["conclusion"].lower())

    def test_negated_must_is_preserved(self):
        response = {"conclusion": "You do not need to submit a notification for this activity."}
        out, _ = EvidencePreservingSemanticVerifier().apply(response, [])
        self.assertIn("do not need", out["conclusion"].lower())

    def test_asserted_claim_still_removed(self):
        response = {"conclusion": "BioSafe can certify your compliance status."}
        out, audit = EvidencePreservingSemanticVerifier().apply(response, [])
        self.assertNotIn("can certify", out["conclusion"].lower())
        self.assertTrue(any(item.get("action") == "remove" for item in audit))
if __name__ == "__main__":
    unittest.main()
