import json
import unittest
from pathlib import Path


HERE=Path(__file__).resolve().parents[1]
PACKET=HERE/"reports/authorization_claim_source_extraction_packet_v0_1.json"


class AuthorizationClaimSourceExtractionPacketTests(unittest.TestCase):
    def test_packet_is_offline_and_not_promoted(self):
        packet=json.loads(PACKET.read_text(encoding="utf-8"))
        self.assertFalse(packet["live_retrieval_connected"])
        self.assertEqual(packet["promotion_status"],"NOT_PROMOTED")
        self.assertEqual(packet["review_status"],"PENDING_CLAIM_LEVEL_REVIEW")

    def test_only_queued_source_claims_are_extracted(self):
        packet=json.loads(PACKET.read_text(encoding="utf-8"))
        self.assertEqual({x["source_claim_id"] for x in packet["entries"]},{"CLM-005","CLM-007"})
        self.assertEqual(packet["source"]["source_sha256"],"6e8364d8e7015738863ed9194a62d16ec62f18c85f338e438a533ed98d83a756")

    def test_decision_fields_remain_unresolved(self):
        packet=json.loads(PACKET.read_text(encoding="utf-8"))
        for entry in packet["entries"]:
            self.assertIsNone(entry["candidate_concept"])
            self.assertIsNone(entry["candidate_polarity"])
            self.assertEqual(entry["currentness"],"UNRESOLVED")
            self.assertEqual(entry["support_spans"],[])
            self.assertTrue(entry["blocking_reasons"])

    def test_exemption_is_not_general_non_requirement(self):
        packet=json.loads(PACKET.read_text(encoding="utf-8"))
        entry=next(x for x in packet["entries"] if x["source_claim_id"]=="CLM-007")
        self.assertIn("EXEMPTION_IS_NOT_A_GENERAL_NO_NOTIFICATION_DETERMINATION",entry["blocking_reasons"])


if __name__=="__main__":
    unittest.main()