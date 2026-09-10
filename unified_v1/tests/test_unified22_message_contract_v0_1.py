
import sys,json
from pathlib import Path
ROOT=Path("/home/khengoon/biosafe")
for p in (ROOT/"src",ROOT/"unified_v1"/"src"):
    sys.path.insert(0,str(p))
from biosafe_pipeline_v0_3_2 import BioSafePipelineV032
from context_budget_manager_v0_1 import select_profile
import full_inference_service_v0_1 as frozen
from biosafe_unified22 import load_constitution,augment_compact_messages,assert_clean_query_preserved

q="What is the difference between biosafety and biosecurity?"
pipe=BioSafePipelineV032(ROOT,top_k=3)
bundle,base,*extra=pipe.build_messages(q,safety_class=None)
profile=select_profile("qwen3.5:0.8b")
policy={"mode":"NORMAL","constraints":[]}
before=frozen._compact_messages(base,q,bundle,{},policy,profile,"ask")
after=augment_compact_messages(before,constitution=load_constitution(),
    interaction_context={"intent":"educational_answer","case_state":{},"resolved_reference":None})

checks=[]
def ck(n,c): checks.append((n,bool(c)))
ck("two_role_messages",len(after)==2 and after[0]["role"]=="system" and after[1]["role"]=="user")
ck("constitution_in_system","BIOSAFE BEHAVIORAL CONSTITUTION" in after[0]["content"])
ck("constitution_not_in_user_payload","BIOSAFE BEHAVIORAL CONSTITUTION" not in after[1]["content"])
ck("clean_query_preserved",assert_clean_query_preserved(before,after))
payload=json.loads(after[1]["content"])
ck("user_query_exact",payload.get("user_query")==q)
ck("interaction_context_present",payload.get("interaction_context",{}).get("intent")=="educational_answer")
ck("behavior_contract_present",payload.get("behavior_contract",{}).get("no_invented_regulatory_citations") is True)
failed=[n for n,v in checks if not v]
for n,v in checks: print(f"{n}: {'PASS' if v else 'FAIL'}")
print(f"Unified-2.2 message contract: {len(checks)-len(failed)}/{len(checks)} PASS")
if failed: raise SystemExit(1)
