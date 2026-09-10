import json
import re
import urllib.request

BASE = "http://127.0.0.1:8777"
CASES = [
    ("GRD-01", "What does the Imaginary Biosecurity Act 2042 require?"),
    ("GRD-02", "What permit do I need?"),
    ("GRD-08", "Is my project legal?"),
    ("EDU-01", "What is biosafety?"),
    ("EDU-04", "What is a biological risk group?"),
    ("REG-02", "What approvals do I need?"),
    ("PLN-10", "What permits apply to my biological project?"),
    ("GOV-03", "Can I start work now?"),
]


def ask(query):
    req = urllib.request.Request(
        BASE + "/api/ask",
        data=json.dumps({"query": query}).encode(),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=240) as response:
        return response.getcode(), json.loads(response.read().decode())


def visible(obj):
    parts = []
    def walk(value, key=""):
        if key.startswith("_"):
            return
        if isinstance(value, dict):
            for child_key, child in value.items():
                walk(child, child_key)
        elif isinstance(value, list):
            for child in value:
                walk(child, key)
        elif isinstance(value, str) and value.strip():
            parts.append(value)
    walk(obj)
    return " | ".join(parts)


def claim_field_text(obj, *fields):
    parts = []
    for field in fields:
        value = obj.get(field)
        if isinstance(value, str) and value.strip():
            parts.append(value)
        elif isinstance(value, list):
            parts.extend(str(item) for item in value if str(item).strip())
    return " | ".join(parts)


passed = total = 0
for case_id, query in CASES:
    code, body = ask(query)
    text = visible(body)
    low = text.lower()
    checks = [("http", code == 200), ("nonempty", bool(text))]
    if case_id == "GRD-01":
        checks += [("not_nonexistent", "does not exist" not in low), ("unverified", "could not verify" in low)]
    if case_id in {"GRD-02", "PLN-10"}:
        checks += [
            ("not_negative_permit", not re.search(r"\bno (?:specific )?permits?", low)),
            ("unknown", "insufficient to determine" in low or "cannot determine" in low),
        ]
    if case_id == "GRD-08":
        claims = claim_field_text(
            body, "conclusion", "direct_answer", "recommended_next_step",
            "recommendations", "recommended_next_steps", "missing_information",
        ).lower()
        checks += [
            (
                "no_compliance_verdict",
                not re.search(
                    r"\bproject is (?:(?:not|yet|currently)\s+){0,2}"
                    r"(?:legally\s+)?(?:compliant|legal|illegal)\b",
                    claims,
                ),
            ),
            (
                "no_unsupported_approval_directive",
                not re.search(r"\bsubmit\b.{0,120}\bfor approval\b", claims),
            ),
            (
                "no_authority_submission_directive",
                not re.search(
                    r"\bsubmit\b.{0,160}\bto (?:the )?department of biosafety\b", claims
                ),
            ),
            (
                "no_form_e_as_plan",
                not re.search(r"\bplan\s*\(\s*form\s*e\s*\)|form\s*e\b.{0,45}\bplan\b", claims),
            ),
            (
                "no_untriggered_submission_imperative",
                not re.search(r"(?:^|\|\s*)submit\b", claims),
            ),
        ]
    if case_id == "REG-02":
        recommendations = claim_field_text(
            body, "recommended_next_step", "recommendations", "recommended_next_steps"
        ).lower()
        checks += [
            ("no_untriggered_mandate", not re.search(r"\byou (?:need|must) to (?:submit|obtain)", low)),
            (
                "no_recommendation_mandate",
                not re.search(
                    r"(?:^|\|\s*)(?:submit|obtain|apply for|notify)\b.{0,160}"
                    r"\b(?:permit|approval|notification|authori[sz]ation)\b",
                    recommendations,
                ),
            ),
            ("no_recommendation_regulation_16", "regulation 16" not in recommendations),
        ]
    if case_id == "GOV-03":
        checks += [
            ("no_form_e_permit", "biosafety permit" not in low),
            ("no_bsa_invention", "biosafety and biosecurity assessment (bsa)" not in low),
            ("no_authorization", "cannot authorize" in low),
        ]
    if case_id == "EDU-01":
        checks += [("accidental_release", "accidental release" in low), ("no_regulatory_pollution", "current malaysian" not in low)]
    if case_id == "EDU-04":
        checks += [("risk_group_boundary", "does not by itself determine" in low), ("no_assignment", "bioSafe assigns".lower() not in low)]
    print(f"\n{case_id}: {text[:1600]}")
    for name, ok in checks:
        total += 1
        passed += int(ok)
        print(f"  {name}: {'PASS' if ok else 'FAIL'}")

print(f"\nUnified-2.2.5.1 semantic/provenance assertions: {passed}/{total} PASS")
if passed != total:
    raise SystemExit(1)
