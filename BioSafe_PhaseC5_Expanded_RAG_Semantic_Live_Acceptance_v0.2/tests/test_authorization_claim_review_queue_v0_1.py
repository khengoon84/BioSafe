import json
import sys
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE/"src"))
from authorization_claim_review_queue_v0_1 import build_review_queue


class AuthorizationClaimReviewQueueTests(unittest.TestCase):
    def test_queue_is_offline_and_not_promoted(self):
        queue=build_review_queue()
        self.assertFalse(queue["active_kb_modified"])
        self.assertFalse(queue["live_retrieval_connected"])
        self.assertEqual(queue["claim_use_status"],"REVIEW_REQUIRED_BEFORE_CLAIM_USE")
        self.assertTrue(queue["queue_entries"])
        self.assertTrue(all(item["promotion_status"]=="NOT_PROMOTED" for item in queue["queue_entries"]))

    def test_accepted_drafts_remain_blocked_from_promotion(self):
        packet=json.loads((HERE/"reports/authorization_claim_source_extraction_packet_v0_1.json").read_text())
        self.assertEqual(packet["review_status"],"HUMAN_REVIEW_ACCEPTED_DRAFT_PENDING_SOURCE_RECONCILIATION")
        self.assertEqual(packet["promotion_status"],"NOT_PROMOTED")
        for entry in packet["entries"]:
            self.assertEqual(entry["human_review_status"],"HUMAN_REVIEW_ACCEPTED_DRAFT")
            self.assertIn("COMPLETE_AMENDMENT_AND_CLAIM_CURRENTNESS_REVIEW_REQUIRED",entry["blocking_reasons"])

    def test_source_backed_candidates_have_unresolved_decision_fields(self):
        queue=build_review_queue()
        ids={item["source_claim_id"] for item in queue["queue_entries"]}
        self.assertEqual(ids,{"CLM-005","CLM-007"})
        for item in queue["queue_entries"]:
            self.assertIsNone(item["candidate_concept"])
            self.assertIsNone(item["candidate_polarity"])
            self.assertIsNone(item["jurisdiction"])
            self.assertEqual(item["human_review_status"],"PENDING_CLAIM_LEVEL_REVIEW")
            self.assertEqual(item["currentness"],"UNRESOLVED")

    def test_notification_quality_is_not_reinterpreted_as_authorization(self):
        queue=build_review_queue()
        excluded={item["source_claim_id"]:item for item in queue["excluded_related_claims"]}
        self.assertEqual(excluded["CLM-006"]["claim_type"],"notification_quality")
        self.assertEqual(excluded["CLM-006"]["promotion_status"],"EXCLUDED_FROM_AUTHORIZATION_QUEUE")

    def test_queue_round_trips_as_json(self):
        json.dumps(build_review_queue())


if __name__=="__main__":
    unittest.main()