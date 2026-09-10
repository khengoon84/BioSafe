# BioSafe Unified-2.2 Constitution-Aware Response Generation v0.1

## Purpose
Experimental generation-layer adapter that adds the BioSafe Behavioral Constitution through the existing `system` role while preserving the clean retrieval query.

## Architecture
- 8768 = Unified-2.1 baseline
- 8769 = Unified-2.2 experimental A/B service
- Frozen inference/RAG files are not edited.

## Install
```bash
python scripts/install_unified22_v0_1.py
```

## Deterministic message-contract test
```bash
/home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/unified_v1/tests/test_unified22_message_contract_v0_1.py
```

## Start 8769
```bash
cd /home/khengoon/biosafe
source .venv/bin/activate
PYTHONPATH=/home/khengoon/biosafe/unified_v1/src python /home/khengoon/biosafe/cra_v1/scripts/run_unified22_sidecar_v0_1.py
```

## A/B regression
Keep both 8768 and 8769 running:
```bash
/home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/cra_v1/tests/live_ab_unified22_v0_1.py
```

## Acceptance
Do not freeze Unified-2.2 solely on hard assertions. Review actual A/B wording for:
- directness;
- conversational relevance;
- regulatory caution;
- absence of duplicate scaffolding;
- preserved uncertainty;
- no invented citations/sections.
