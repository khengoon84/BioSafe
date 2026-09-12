import sys
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE/"src"))
from environment_preflight import evaluate


class EnvironmentPreflightTests(unittest.TestCase):
    def test_live_acceptance_is_blocked_until_candidate_inference_bridge_exists(self):
        report=evaluate()
        self.assertEqual(report["candidate_service_inference_enabled"],True)
        self.assertIn(report["result"],{"READY_FOR_C5_LIVE_SERVICE_PREFLIGHT","BLOCKED_ENVIRONMENT_NOT_VALIDATED"})
        self.assertFalse(report["live_execution_performed"])
        self.assertEqual(report["live_activation_status"],"PROHIBITED_PENDING_PHASE_C_GATES")

    def test_expected_model_identity_is_reported(self):
        report=evaluate()
        self.assertEqual(set(report["models"]),{"qwen3.5:0.8b","qwen3.5:2b"})
        if report["models"]["qwen3.5:0.8b"]["present"]:
            self.assertEqual(report["models"]["qwen3.5:0.8b"]["digest"],"f3817196d142eaf72ce79dfebe53dcb20bd21da87ce13e138a8f8e10a866b3a4")


if __name__=="__main__":
    unittest.main()