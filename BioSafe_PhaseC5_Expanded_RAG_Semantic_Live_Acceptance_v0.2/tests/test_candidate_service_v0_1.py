import sys
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE/"src"))
from candidate_service_v0_1 import app


class CandidateServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client=app.test_client()

    def test_health_is_candidate_only_and_inference_disabled(self):
        response=self.client.get("/health"); self.assertEqual(response.status_code,200)
        body=response.get_json(); self.assertEqual(body["candidate"],"C37_METADATA_CFG02:metadata_off")
        self.assertTrue(body["inference_enabled"]); self.assertTrue(body["ollama_call_enabled"]); self.assertTrue(body["evaluation_only_serialized_service"]); self.assertFalse(body["frozen_core_modified"]); self.assertFalse(body["active_kb_modified"])
        self.assertEqual(body["hash_errors"],[])

    def test_inspection_returns_separate_paths_and_candidate_origin(self):
        response=self.client.post("/api/inspect-retrieval",json={"query":"What is biological risk?"})
        self.assertEqual(response.status_code,200); body=response.get_json()
        self.assertEqual(body["candidate_path_id"],"C37_METADATA_CFG02:metadata_off")
        self.assertNotEqual(body["baseline"]["path_id"],body["candidate"]["path_id"])
        self.assertTrue(all(item["evidence_origin"]=="C5_REVIEWED_CANDIDATE" for item in body["candidate"]["evidence"]))

    def test_rollback_endpoint_is_explicitly_available(self):
        body=self.client.post("/api/rollback-check").get_json()
        self.assertEqual(body["status"],"AVAILABLE"); self.assertTrue(body["candidate_disabled"]); self.assertTrue(body["automatic_reopen_on_failure"])

    def test_missing_query_is_rejected(self):
        self.assertEqual(self.client.post("/api/inspect-retrieval",json={}).status_code,400)

    def test_candidate_ask_is_bound_to_candidate_path_without_calling_ollama(self):
        import full_inference_service_v0_1 as frozen
        original=frozen._ollama
        def fake(model,messages,num_predict):
            payload=__import__("json").loads(messages[1]["content"])
            assert payload["candidate_path_id"]=="C37_METADATA_CFG02:metadata_off"
            assert payload["evidence_bundle"]
            return {"conclusion":"The reviewed candidate evidence was received.","missing_information":[],"recommended_next_step":[]},True,{"done_reason":"stop","model":model}
        frozen._ollama=fake
        try:
            response=self.client.post("/api/ask",json={"query":"What is the purpose of a biosafety risk assessment?"})
            self.assertEqual(response.status_code,200); body=response.get_json(); self.assertTrue(body["_meta"]["candidate_inference_bridge"]); self.assertEqual(body["_meta"]["candidate_path_id"],"C37_METADATA_CFG02:metadata_off")
        finally:
            frozen._ollama=original

    def test_protected_internal_request_fields_are_not_used(self):
        import full_inference_service_v0_1 as frozen
        original=frozen._ollama
        def fake(model,messages,num_predict):
            payload=__import__("json").loads(messages[1]["content"])
            assert payload["candidate_path_id"]=="C37_METADATA_CFG02:metadata_off"
            return {"conclusion":"Evidence-backed candidate response.","missing_information":[],"recommended_next_step":[]},True,{"done_reason":"stop","model":model}
        frozen._ollama=fake
        try:
            response=self.client.post("/api/ask",json={"query":"What is the purpose of a biosafety risk assessment?","intent":"simple_answer","model":"wrong","candidate_path_id":"wrong"})
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.get_json()["_meta"]["ignored_protected_request_fields"],["candidate_path_id","intent","model"])
        finally:
            frozen._ollama=original


if __name__=="__main__": unittest.main()