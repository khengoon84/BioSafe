
from __future__ import annotations
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path("/home/khengoon/biosafe")
for p in (PROJECT_ROOT, PROJECT_ROOT/"src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from full_inference_service_v0_1 import BioSafeFullInferenceServiceV01

class BioSafeLocalService:
    def __init__(self, project_root: str | Path = PROJECT_ROOT):
        self.engine = BioSafeFullInferenceServiceV01(project_root)

    def run_query(self, query: str) -> dict[str, Any]:
        return self.engine.infer(query, workflow="ask")

    def review_document(self, query: str, filename: str, text: str) -> dict[str, Any]:
        return self.engine.infer(
            query, documents=[{"filename": filename, "text": text}],
            workflow="document_review"
        )

    def form_e(self, query: str) -> dict[str, Any]:
        q = (
            "Assist with Malaysian Form E using only information supplied by the user. "
            "Do not fabricate missing fields, make an official legal determination, "
            "or simulate IBC assessment or approval.\n\n" + query
        )
        return self.engine.infer(q, workflow="form_e")
