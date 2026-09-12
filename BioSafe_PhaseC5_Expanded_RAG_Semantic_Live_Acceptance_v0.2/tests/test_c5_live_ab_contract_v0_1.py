import json
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
REPORTS=[HERE/"reports/c5_live_ab_report_v0_2.json",HERE/"reports/c5_live_ab_report_v0_3.json"]

def validate_report(case, path: Path):
    data=json.loads(path.read_text())
    case.assertEqual(data["artifact_version"].split("_v")[-1].replace(".","_"),path.stem.split("_v")[-1])
    case.assertIn(data["result"],{"READY_FOR_C5_REPEATED_GENERATION","BLOCKED_CORRECTION_REQUIRED","INCOMPLETE_RUN_NOT_SCORED"})
    case.assertEqual(data["live_activation_status"],"PROHIBITED_PENDING_PHASE_C_GATES")
    case.assertEqual(len(data["runs"]["baseline"]),len(data["cases"]));case.assertEqual(len(data["runs"]["candidate"]),len(data["cases"]))
    case.assertTrue(data["complete"] or data["result"] in {"INCOMPLETE_RUN_NOT_SCORED","BLOCKED_CORRECTION_REQUIRED"})
    if data["complete"]:
        case.assertEqual(len(data["runs"]["baseline"]),len(data["cases"]))
        case.assertEqual(len(data["runs"]["candidate"]),len(data["cases"]))
    return data

class LiveABReportTests(unittest.TestCase):
    def test_report_is_present_and_guarded(self):
        for report in REPORTS:
            if not report.exists(): self.skipTest(f"live A/B suite not run: {report.name}")
            validate_report(self,report)

    def test_corrected_v0_3_report_carries_grd_02_fail_closed_gate(self):
        report=HERE/"reports/c5_live_ab_report_v0_3.json"
        if not report.exists(): self.skipTest("corrected v0_3 live A/B suite not run")
        data=validate_report(self,report)
        for run in data["runs"]["candidate"]:
            if run.get("case_id")!="GRD-02": continue
            body=run.get("response") or {}
            self.assertIs(body.get("_meta",{}).get("model_called"),False)
            self.assertTrue(body.get("authorization_gate",{}).get("missing_facts"))
            self.assertEqual(body.get("safety",{}).get("status"),"FAIL_CLOSED")

if __name__=="__main__":unittest.main()