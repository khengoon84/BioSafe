
from __future__ import annotations
import json
import re
from typing import Any

def recover_compact_reasoning(content: str) -> tuple[dict[str, Any] | None, bool, str | None]:
    """
    Parse the compact three-field Qwen response.
    If JSON is truncated, recover only complete, explicitly present fields.
    Never invent missing content.
    """
    try:
        obj = json.loads(content)
        if isinstance(obj, dict):
            return obj, True, None
    except Exception as exc:
        parse_err = str(exc)
    else:
        parse_err = "Output was not a JSON object."

    text = content or ""
    out: dict[str, Any] = {}

    m = re.search(r'"conclusion"\s*:\s*"((?:[^"\\]|\\.)*)"', text, flags=re.S)
    if m:
        try:
            out["conclusion"] = json.loads('"' + m.group(1) + '"')
        except Exception:
            pass

    for field in ("missing_information", "recommended_next_step"):
        m = re.search(rf'"{field}"\s*:\s*\[(.*?)\]', text, flags=re.S)
        if not m:
            continue
        try:
            out[field] = json.loads("[" + m.group(1) + "]")
        except Exception:
            pass

    required = {"conclusion", "missing_information", "recommended_next_step"}
    if required.issubset(out):
        return out, False, "Recovered complete compact fields from truncated JSON."

    return None, False, parse_err
