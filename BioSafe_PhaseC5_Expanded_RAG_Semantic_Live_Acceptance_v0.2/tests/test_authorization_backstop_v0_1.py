"""Deterministic tests for the C5-only authorization backstop (defense in depth)."""
import json
import sys
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE/"src"))
from authorization_backstop_v0_1 import FAIL_CLOSED_MESSAGE, apply_authorization_backstop, load_support_types


class AuthorizationBackstopTests(unittest.TestCase):
    def test_support_types_are_config_driven(self):
        support=load_support_types()
        self.assertIn("permit_requirement",support["permit"])
        self.assertNotIn("forme",support["permit"])

    def test_unsupported_permit_claim_is_removed_with_audit(self):
        response={"conclusion":"You need a Biosafety Permit (BP) for the described activity.","evidence":[]}
        guarded,audit=apply_authorization_backstop(response)
        self.assertEqual(guarded["conclusion"],FAIL_CLOSED_MESSAGE)
        self.assertEqual(guarded["safety"]["status"],"FAIL_CLOSED")
        self.assertIn("UNSUPPORTED_AUTHORIZATION_CLAIM_REMOVED",guarded["safety"]["reason_codes"])
        self.assertEqual(len(audit),1)
        self.assertEqual(audit[0]["action"],"unsupported_authorization_claim_removed")
        self.assertEqual(audit[0]["reason_codes"],["NO_EVIDENCE_SUPPORT"])
        self.assertIn(audit[0]["claim"],"You need a Biosafety Permit (BP) for the described activity.")
        self.assertEqual(guarded["_meta"]["authorization_backstop"][0]["action"],"unsupported_authorization_claim_removed")
        json.dumps(guarded)

    def test_supported_claim_is_preserved(self):
        response={"conclusion":"You need a permit for contained use.","evidence":[{"claim_type":"permit_requirement"}]}
        guarded,audit=apply_authorization_backstop(response)
        self.assertEqual(guarded["conclusion"],response["conclusion"])
        self.assertEqual(audit,[])
        self.assertNotIn("authorization_backstop",guarded.get("_meta",{}))

    def test_output_without_authorization_claim_is_unchanged(self):
        response={"conclusion":"The reviewed candidate evidence was received.","recommended_next_step":["Record the observation."],"evidence":[]}
        guarded,audit=apply_authorization_backstop(response)
        self.assertEqual(guarded["conclusion"],response["conclusion"])
        self.assertEqual(guarded["recommended_next_step"],response["recommended_next_step"])
        self.assertEqual(audit,[])

    def test_blank_output_is_unchanged(self):
        guarded,audit=apply_authorization_backstop({"conclusion":""})
        self.assertEqual(guarded["conclusion"],"")
        self.assertEqual(audit,[])

    def test_forme_evidence_never_supports_a_permit_claim(self):
        response={"conclusion":"You need a Biosafety Permit (Form E).","evidence":[{"claim_type":"forme"},{"claim_type":"forme_cbi"}]}
        guarded,audit=apply_authorization_backstop(response)
        self.assertEqual(guarded["conclusion"],FAIL_CLOSED_MESSAGE)
        self.assertEqual(len(audit),1)

    def test_notification_claim_requires_notification_requirement_claim_type(self):
        unsupported,audit_a=apply_authorization_backstop({"conclusion":"You need to submit a notification for the described activity.","evidence":[{"claim_type":"risk_assessment"}]})
        self.assertEqual(unsupported["conclusion"],FAIL_CLOSED_MESSAGE); self.assertTrue(audit_a)
        supported,audit_b=apply_authorization_backstop({"conclusion":"You need to submit a notification for the described activity.","evidence":[{"claim_type":"notification_requirement"}]})
        self.assertNotEqual(supported["conclusion"],FAIL_CLOSED_MESSAGE); self.assertEqual(audit_b,[])

    def test_list_fields_are_screened(self):
        response={"recommended_next_step":["You need to obtain a permit from the department.","Record the observation."],"evidence":[]}
        guarded,audit=apply_authorization_backstop(response)
        self.assertEqual(guarded["recommended_next_step"],["Record the observation."])
        self.assertEqual(len(audit),1); self.assertEqual(audit[0]["field"],"recommended_next_step")

    def test_mixed_conclusion_keeps_supported_sentences_and_fails_closed(self):
        response={"conclusion":"You need a Biosafety Permit (BP) for the described activity. Waste must be handled under the institution's procedures.","evidence":[]}
        guarded,audit=apply_authorization_backstop(response)
        self.assertEqual(guarded["conclusion"],FAIL_CLOSED_MESSAGE)
        self.assertEqual(len(audit),1)

    def test_multi_noun_claim_requires_support_for_every_noun(self):
        response={"conclusion":"An approval is required and you need a permit.","evidence":[{"claim_type":"approval_requirement"}]}
        guarded,audit=apply_authorization_backstop(response)
        self.assertEqual(guarded["conclusion"],FAIL_CLOSED_MESSAGE)
        self.assertEqual(len(audit),1)

    def test_deterministic_repeat(self):
        response={"conclusion":"A permit is required for transport.","evidence":[]}
        first=apply_authorization_backstop(dict(response))[0]
        second=apply_authorization_backstop(dict(response))[0]
        self.assertEqual(json.dumps(first,sort_keys=True),json.dumps(second,sort_keys=True))


if __name__=="__main__":unittest.main()
