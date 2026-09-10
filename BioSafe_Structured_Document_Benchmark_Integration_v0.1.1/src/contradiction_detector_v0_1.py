
from __future__ import annotations

DEFAULT_CANONICAL_MAP = {
    "host_organism": "organism_identity",
    "organism_or_material": "organism_identity",
    "organism_identity": "organism_identity",
    "insert_or_construct": "construct_identity",
    "construct_or_insert": "construct_identity",
    "containment_or_facility": "containment",
    "facility_or_containment": "containment",
    "containment": "containment",
}

def _norm(value):
    if value is None:
        return None
    return " ".join(str(value).lower().split())

def _canonical_fact_map(doc: dict, canonical_map: dict | None = None) -> dict:
    cmap = canonical_map or DEFAULT_CANONICAL_MAP
    out = {}
    for fact in doc.get("facts", []):
        if fact.get("status") != "present":
            continue
        original = fact.get("field")
        canonical = cmap.get(original, original)
        out[canonical] = fact
    return out

def compare_fact_sets(
    doc_a: dict,
    doc_b: dict,
    comparable_fields: list[str] | None = None,
    canonical_map: dict | None = None,
) -> list[dict]:
    a = _canonical_fact_map(doc_a, canonical_map)
    b = _canonical_fact_map(doc_b, canonical_map)
    fields = set(a) & set(b)

    if comparable_fields is not None:
        cmap = canonical_map or DEFAULT_CANONICAL_MAP
        wanted = {cmap.get(x, x) for x in comparable_fields}
        fields &= wanted

    out = []
    for field in sorted(fields):
        va, vb = _norm(a[field].get("value")), _norm(b[field].get("value"))
        if va is None or vb is None:
            continue
        if va != vb:
            out.append({
                "field": field,
                "document_a": doc_a.get("document_id", "A"),
                "value_a": a[field].get("value"),
                "document_b": doc_b.get("document_id", "B"),
                "value_b": b[field].get("value"),
                "status": "possible"
            })
    return out
