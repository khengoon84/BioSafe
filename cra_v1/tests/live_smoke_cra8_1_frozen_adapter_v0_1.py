import sys, json
from pathlib import Path
ROOT=Path("/home/khengoon/biosafe")
sys.path.insert(0,str(ROOT/"cra_v1"/"src"))

from cra_contracts_v0_1 import *
from frozen_inference_rag_adapter_v0_1 import FrozenInferenceRAGAdapterV01

frame=TaskFrame(
    task_id="live",
    interaction_type=InteractionType.NEW_TASK,
    user_goal="answer",
    current_question="What general factors should I consider in a biosafety risk assessment?",
    jurisdiction="Malaysia",
    activated_domains=["general_biosafety"],
    inactive_domains=["form_e","transport","waste"]
)
plan=EvidencePlan(
    skip_rag=False,
    required_domains=["general_biosafety"],
    required_evidence_types=["risk_assessment","general_biosafety_guidance"],
    preferred_authority_tiers=[1,2],
    exclude_domains=["form_e","transport","waste"],
    jurisdiction="Malaysia"
)
adapter=FrozenInferenceRAGAdapterV01(project_root=ROOT)
result=adapter.run(
    frame,plan,
    {"skip":False,"required_domains":["general_biosafety"],"exclude_domains":["form_e","transport","waste"]},
    workflow="ask"
)
print(json.dumps({
    "conclusion":result.response.get("conclusion"),
    "safety":result.response.get("safety"),
    "adapter_meta":result.adapter_meta,
},indent=2,ensure_ascii=False))
print("CRA-8.1 optional live smoke: PASS")
