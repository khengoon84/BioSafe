
from __future__ import annotations
import argparse, json
from pathlib import Path

def load(path: Path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jsonl")
    ap.add_argument("--output", default=None)
    args = ap.parse_args()

    path = Path(args.jsonl)
    rows = load(path)
    model_calls = [r for r in rows if r.get("model_called")]
    decisions = {}
    for r in rows:
        decisions[r.get("final_decision")] = decisions.get(r.get("final_decision"), 0) + 1

    report = {
        "cases": len(rows),
        "model_calls": len(model_calls),
        "valid_final_json": sum(1 for r in rows if r.get("valid_json")),
        "compact_model_json_valid": sum(1 for r in model_calls if r.get("compact_model_json_valid")),
        "decisions": decisions,
        "length_exhaustions": sum(
            1 for r in model_calls if (r.get("metrics") or {}).get("done_reason") == "length"
        ),
        "contradiction_fallbacks": sum(1 for r in rows if r.get("contradiction_fallback_used")),
        "cases_with_repairs": sum(1 for r in rows if r.get("deterministic_repairs")),
        "context_budget_hard_exceedances": sum(
            1 for r in rows
            if r.get("context_budget") and not r["context_budget"].get("within_hard_budget", True)
        ),
        "case_status": [
            {
                "case_id": r.get("case_id"),
                "decision": r.get("final_decision"),
                "valid_json": r.get("valid_json"),
                "compact_model_json_valid": r.get("compact_model_json_valid"),
                "done_reason": (r.get("metrics") or {}).get("done_reason"),
                "repairs": r.get("deterministic_repairs") or [],
            }
            for r in rows
        ],
    }

    out = Path(args.output) if args.output else path.with_name(path.stem + "_audit.json")
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print("Standard-Calibrated audit written to:", out)

if __name__ == "__main__":
    main()
