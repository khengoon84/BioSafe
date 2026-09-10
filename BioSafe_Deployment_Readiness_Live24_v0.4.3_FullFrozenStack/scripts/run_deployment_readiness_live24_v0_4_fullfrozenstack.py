
from __future__ import annotations
import json, sys, time, urllib.request
from pathlib import Path

PROJECT = Path("/home/khengoon/biosafe")
sys.path.insert(0, str(PROJECT))
sys.path.insert(0, str(PROJECT/"src"))

from biosafe_pipeline_v0_3_2 import BioSafePipelineV032
from policy_decision_guard_v0_3_2 import classify_policy, build_policy_instruction
from integration_safety_gate_v0_1_2 import classify_safety
from structured_document_benchmark_adapter_v0_1 import BioSafeStructuredBenchmarkAdapterV01
from user_document_evidence_adapter_v0_1 import merge_document_evidence_into_bundle
from document_context_evidence_filter_v0_1 import filter_document_review_evidence
from document_evidence_alias_normalizer_v0_1 import normalize_document_evidence_aliases
from document_fact_precedence_guard_v0_1 import enforce_document_fact_precedence
from document_decision_guard_v0_1 import apply_document_decision_guard
from complexity_escalation_router_v0_1 import ComplexityEscalationRouterV01
from context_budget_manager_v0_1 import select_profile, budget_evidence, compact_packet_for_budget, response_contract, audit_prompt
from deterministic_response_assembler_v0_1 import assemble_biosafe_response
from output_normalizer_v0_3_2 import normalize_output
from policy_shell_enforcer_v0_3_2 import enforce_policy_shell
from regulatory_language_guard_v0_1 import RegulatoryLanguageGuardV011
from response_budget_guard_v0_1 import enforce_response_budget
from output_validator_v0_2 import validate_output
from boundary_validator_v0_3_2 import validate_boundaries

OLLAMA_URL = "http://localhost:11434/api/chat"


def unpack_pipeline_messages(result):
    """
    Accept BioSafePipelineV032 build_messages() return values without assuming
    the historical 2-value interface. Identify bundle/messages by structure.
    """
    items = list(result) if isinstance(result, (tuple, list)) else [result]
    bundle = None
    messages = None
    extras = []

    for item in items:
        if isinstance(item, dict) and bundle is None and (
            "evidence_bundle" in item or "route" in item or "user_query" in item
        ):
            bundle = item
            continue

        if isinstance(item, list) and messages is None:
            if all(isinstance(x, dict) and "role" in x and "content" in x for x in item):
                messages = item
                continue

        extras.append(item)

    if bundle is None or messages is None:
        raise RuntimeError(
            "Could not identify bundle/messages from BioSafePipelineV032.build_messages() "
            f"return value. Types: {[type(x).__name__ for x in items]}"
        )
    return bundle, messages, extras


def ollama_chat(model, messages, num_predict):
    body = json.dumps({
        "model": model,
        "messages": messages,
        "stream": False,
        "think": False,
        "options": {"temperature": 0, "num_predict": int(num_predict)}
    }).encode()
    req = urllib.request.Request(OLLAMA_URL, data=body, headers={"Content-Type":"application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=900) as r:
        payload = json.loads(r.read().decode())
    return payload, time.time()-t0

def strip_fences(text):
    t = (text or "").strip()
    if t.startswith("```"):
        lines = t.splitlines()
        if lines and lines[0].startswith("```"): lines = lines[1:]
        if lines and lines[-1].strip() == "```": lines = lines[:-1]
        t = "\n".join(lines).strip()
    return t

def parse_json(text):
    try:
        obj = json.loads(strip_fences(text))
        return (obj if isinstance(obj, dict) else None), isinstance(obj, dict)
    except Exception:
        return None, False

def policy_dict(decision):
    if hasattr(decision, "to_dict"):
        return decision.to_dict()
    return {
        "short_circuit": getattr(decision, "short_circuit", False),
        "mode": getattr(decision, "mode", "NORMAL"),
        "constraints": getattr(decision, "constraints", []),
        "reason": getattr(decision, "reason", ""),
        "matched_rules": getattr(decision, "matched_rules", []),
        "deterministic_response": getattr(decision, "deterministic_response", None),
    }

DOC_PREFIX_MAP = {
    # Structured benchmark adapter recognizes these exact prefixes.
    "sop1":"SOP-03", "sop2":"SOP-01", "sop3":"SOP-01", "sop4":"SOP-03",
    "sop5":"SOP-03", "sop7":"SOP-03",
    "prop1":"PROP-01", "prop2":"PROP-01", "prop3":"PROP-02", "prop4":"PROP-01",
    "prop5":"PROP-01", "prop6":"PROP-01", "prop7":"PROP-01",
    "forme1":"FORM-E-SYNTHETIC-STRUCTURE",
    "forme2":"FORM-E-SYNTHETIC-COMPLETED",
    "forme4":"FORM-E-SYNTHETIC-COMPLETED",
    "forme5":"FORM-E-SYNTHETIC-STRUCTURE",
    "forme6":"FORM-E-SYNTHETIC-STRUCTURE",
    "forme7":"FORM-E-SYNTHETIC-COMPLETED",
}
def doc_filename(doc):
    prefix=DOC_PREFIX_MAP.get(doc["id"])
    if not prefix:
        raise KeyError(f"No structured benchmark prefix mapped for document id {doc['id']}")
    return f"{prefix}-{doc['id']}.txt"

def compact_messages(base_messages, case, bundle, packet, policy, profile):
    # Use the system prompt from the installed v0.3.2 pipeline.
    system = base_messages[0]["content"] if base_messages else "You are BioSafe."

    ev, ev_audit = budget_evidence(bundle.get("evidence_bundle", []), profile)
    compact_packet = compact_packet_for_budget(packet, profile) if packet else {}
    contract = response_contract(profile)

    payload = {
        "task": "Provide compact BioSafe reasoning using only supplied evidence, document findings and policy constraints.",
        "case_id": case["id"],
        "user_query": case["query"],
        "policy": policy,
        "policy_instruction": build_policy_instruction_obj(policy),
        "route": bundle.get("route", {}),
        "evidence_bundle": ev,
        "structured_document_findings": compact_packet,
        "response_contract": contract,
        "required_output_fields": [
            "conclusion",
            "missing_information",
            "recommended_next_step"
        ]
    }
    messages = [
        {"role":"system", "content":system},
        {"role":"user", "content":json.dumps(payload, ensure_ascii=False, indent=2)}
    ]
    try:
        prompt_audit = audit_prompt(profile.model_id, messages, ev_audit)
    except Exception as e:
        prompt_audit = {"error": repr(e)}
    return messages, ev, ev_audit, prompt_audit

def build_policy_instruction_obj(policy):
    # build_policy_instruction expects the PolicyDecision object in some installed builds,
    # but the compact harness already carries mode/constraints explicitly.
    constraints = policy.get("constraints", [])
    mode = policy.get("mode", "NORMAL")
    return f"Policy mode: {mode}. Constraints: " + "; ".join(constraints)

def main():
    cases = json.loads((PROJECT/"data"/"deployment_readiness_cases_v0.1.json").read_text(encoding="utf-8"))
    fixtures = json.loads((PROJECT/"data"/"deployment_readiness_document_fixtures_v0.1.json").read_text(encoding="utf-8"))

    pipeline = BioSafePipelineV032(root=PROJECT, top_k=3)
    doc_adapter = BioSafeStructuredBenchmarkAdapterV01(PROJECT)
    router = ComplexityEscalationRouterV01()
    reg_guard = RegulatoryLanguageGuardV011()
    results = []

    for i, case in enumerate(cases, 1):
        print(f"[{i:02d}/24] {case['id']}", flush=True)
        t0 = time.time()
        try:
            hard_safety = classify_safety(case["query"])
            hard_safety_restricted = bool(getattr(hard_safety, "restricted", False))

            decision = classify_policy(case["query"])
            pd = policy_dict(decision)

            # Actual integration hard safety gate precedes policy classification.
            if hard_safety_restricted:
                final = {
                    "conclusion":"I can help assess biosafety or biosecurity risk, but I cannot provide instructions for increasing harmful biological capability or defeating containment.",
                    "applicable_authority":[],
                    "evidence":[],
                    "missing_information":[],
                    "recommended_next_step":[
                        "Reframe the request around risk reduction, containment, safe handling, incident prevention, or other non-enabling biosafety objectives."
                    ],
                    "limitations":[
                        "BioSafe does not provide actionable assistance that increases harmful biological capability or bypasses containment."
                    ],
                    "safety":{
                        "classification":"refusal",
                        "response_mode":"refuse_and_redirect",
                        "reason":"restricted_biological_capability"
                    }
                }
                results.append({
                    "case_id":case["id"], "group":case["group"],
                    "expected_route":case.get("expected_route"),
                    "observed_route":"deterministic_safety",
                    "hard_safety_restricted":True,
                    "policy":pd, "model_called":False,
                    "valid_json_first_pass":True,
                    "wall_seconds":round(time.time()-t0,4),
                    "final_response":final,
                    "error":None
                })
                continue

            # Policy-guard short circuit, if separately applicable.
            if pd.get("short_circuit"):
                final = pd.get("deterministic_response") or {
                    "conclusion":"I can’t provide instructions that increase harmful biological capability or help bypass containment. I can help with high-level biosafety and risk-reduction principles.",
                    "applicable_authority":[],
                    "evidence":[],
                    "missing_information":[],
                    "recommended_next_step":["Reframe the request around risk reduction, containment, or safe handling."],
                    "limitations":["Restricted biological-capability assistance is not provided."],
                    "safety":{"classification":"refusal","response_mode":"refuse_and_redirect","reason":pd.get("reason","restricted")}
                }
                results.append({
                    "case_id":case["id"], "group":case["group"],
                    "expected_route":case.get("expected_route"),
                    "observed_route":"deterministic_safety",
                    "policy":pd, "model_called":False,
                    "valid_json_first_pass":True,
                    "wall_seconds":round(time.time()-t0,4),
                    "final_response":final,
                    "error":None
                })
                continue

            bundle, base_messages, pipeline_extras = unpack_pipeline_messages(
                pipeline.build_messages(case["query"], case_id=case["id"], safety_class=None)
            )

            analysed_docs = []
            for d in case.get("documents", []):
                text = fixtures.get(d["id"], "")
                analysed_docs.append(doc_adapter.analyse(doc_filename(d), text))

            packet = {}
            if analysed_docs:
                packet = doc_adapter.build_packet(
                    case["query"], analysed_docs, bundle.get("evidence_bundle", []), pd.get("mode","NORMAL")
                )
                bundle = merge_document_evidence_into_bundle(bundle, packet, max_items=6)

                # Preserve the existing document-review evidence filter.
                doc_types = [d.get("type","") for d in case.get("documents",[])]
                filtered, filter_audit = filter_document_review_evidence(
                    case["query"], doc_types, bundle.get("evidence_bundle", [])
                )
                bundle["evidence_bundle"] = filtered
            else:
                filter_audit = {}

            routing_packet = packet if packet else {
                "documents": case.get("documents", []),
                "missing_fields": case.get("missing_fields", []),
                "contradictions": case.get("contradictions", [])
            }

            lite_result = case.get("simulated_lite_result")
            route_decision = router.route(routing_packet, lite_result) if lite_result is not None else router.route(routing_packet)
            model = route_decision["model"]
            profile = select_profile(model)

            messages, budgeted_ev, ev_audit, prompt_audit = compact_messages(
                base_messages, case, bundle, packet, pd, profile
            )

            payload, model_wall = ollama_chat(model, messages, getattr(profile, "output_token_budget", 420))
            raw = ((payload.get("message") or {}).get("content") or "")
            compact, valid = parse_json(raw)
            if compact is None:
                compact = {
                    "conclusion":"The compact model response could not be reliably parsed.",
                    "missing_information":[],
                    "recommended_next_step":["Review the case through the BioSafe validation pathway."]
                }

            assembled = assemble_biosafe_response(
                compact, bundle,
                max_missing=getattr(profile,"max_missing_findings",3),
                max_recommendations=getattr(profile,"max_recommendations",2),
                max_evidence=getattr(profile,"max_rag_claims",3),
                max_limitations=getattr(profile,"max_limitations",1)
            )

            repairs = []

            if packet:
                assembled, r = normalize_document_evidence_aliases(assembled, bundle.get("evidence_bundle", [])); repairs += r
                assembled, r = enforce_document_fact_precedence(assembled, packet); repairs += r
                assembled, r = apply_document_decision_guard(assembled, packet); repairs += r

            assembled, r = normalize_output(assembled); repairs += r
            assembled, r = enforce_policy_shell(assembled, pd); repairs += r
            assembled, r = reg_guard.apply(assembled, bundle.get("evidence_bundle", [])); repairs += r

            budget_result = enforce_response_budget(
                assembled,
                max_missing=getattr(profile,"max_missing_findings",3),
                max_recommendations=getattr(profile,"max_recommendations",2),
                max_limitations=getattr(profile,"max_limitations",1),
                max_evidence=getattr(profile,"max_rag_claims",3)
            )
            if isinstance(budget_result, tuple) and len(budget_result) == 2:
                assembled, budget_repairs = budget_result
                if isinstance(budget_repairs, list):
                    repairs += budget_repairs
            else:
                assembled = budget_result

            ov = validate_output(assembled, bundle, valid_json=valid)
            bv = validate_boundaries(assembled, pd)

            results.append({
                "case_id":case["id"],
                "group":case["group"],
                "expected_route":case.get("expected_route"),
                "observed_route":model,
                "route_reasons":route_decision.get("reasons",[]),
                "model_called":True,
                "valid_json_first_pass":valid,
                "done_reason":payload.get("done_reason"),
                "model_wall_seconds":round(model_wall,4),
                "wall_seconds":round(time.time()-t0,4),
                "policy":pd,
                "hard_safety_restricted":hard_safety_restricted,
                "route":bundle.get("route"),
                "pipeline_extra_return_values":[repr(x)[:1000] for x in pipeline_extras],
                "evidence_count":len(bundle.get("evidence_bundle",[])),
                "evidence_bundle":bundle.get("evidence_bundle",[]),
                "structured_packet":packet,
                "structured_document_types":[d.get("document_type") for d in analysed_docs],
                "document_filter_audit":filter_audit,
                "context_budget_profile":{
                    "profile_id":getattr(profile,"profile_id",None),
                    "model_id":getattr(profile,"model_id",model),
                    "output_token_budget":getattr(profile,"output_token_budget",None),
                    "max_rag_claims":getattr(profile,"max_rag_claims",None),
                    "max_document_evidence":getattr(profile,"max_document_evidence",None),
                    "max_missing_findings":getattr(profile,"max_missing_findings",None),
                    "max_recommendations":getattr(profile,"max_recommendations",None),
                    "max_limitations":getattr(profile,"max_limitations",None),
                },
                "prompt_audit":prompt_audit,
                "integration_repairs":repairs,
                "output_validation":ov.to_dict() if hasattr(ov,"to_dict") else repr(ov),
                "boundary_validation":bv.to_dict() if hasattr(bv,"to_dict") else repr(bv),
                "raw_model_response":raw,
                "compact_model_output":compact,
                "final_response":assembled,
                "error":None
            })
        except Exception as e:
            results.append({
                "case_id":case["id"], "group":case["group"],
                "expected_route":case.get("expected_route"),
                "wall_seconds":round(time.time()-t0,4),
                "error":repr(e)
            })

    out = {
        "suite":"BioSafe_Deployment_Readiness_Live24_v0.4.3_FullFrozenStack",
        "pipeline":"biosafe_pipeline_v0_3_2.BioSafePipelineV032",
        "architecture_note":"Uses installed frozen stack interfaces, compact generation, deterministic assembly, document guards, regulatory guard, output and boundary validators.",
        "synthetic_document_fixtures":True,
        "cases":len(results),
        "results":results
    }
    outdir = PROJECT/"output"
    outdir.mkdir(exist_ok=True)
    outfile = outdir/"deployment_readiness_live24_v0.4.3_fullfrozenstack_results.json"
    outfile.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print("Output:", outfile)

if __name__ == "__main__":
    main()
