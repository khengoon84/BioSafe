from __future__ import annotations

import csv
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
INGESTION = ROOT / "controlled_sources/ingestion_v0_1"
SRC = INGESTION / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from biosafe_controlled_ingestion.claim_reconciliation import CLAIM_REVIEW_COMPLETE  # noqa: E402
from biosafe_controlled_ingestion.claim_review_aid import (  # noqa: E402
    NO_AUTOMATED_DISPOSITION,
    build_claim_review_aid,
    write_claim_review_aid,
)
from biosafe_controlled_ingestion.components import (  # noqa: E402
    ACTIVATION_PROHIBITED,
    CLAIM_REVIEW_REQUIRED,
)
from biosafe_controlled_ingestion.contracts import ValidationError  # noqa: E402
from biosafe_controlled_ingestion.legal_claim_review_draft import LEGAL_CLAIM_IDS  # noqa: E402


COMPLETED_NONLEGAL_CLAIM_IDS = {
    "CLM-008", "CLM-009", "CLM-010", "CLM-011",
    "CLM-012", "CLM-013", "CLM-014",
    "CLM-015", "CLM-016", "CLM-017",
    "CLM-018", "CLM-019", "CLM-020", "CLM-021",
    "CLM-022", "CLM-023", "CLM-024", "CLM-025",
    "CLM-026", "CLM-027", "CLM-028",
    "CLM-031", "CLM-035",
    "CLM-032", "CLM-033", "CLM-036", "CLM-037", "CLM-038",
    "CLM-039", "CLM-040", "CLM-041", "CLM-044", "CLM-045",
}


PATHS = {
    "crosswalk": INGESTION / "config/document_identity_crosswalk_v0_1.json",
    "review_map": INGESTION / "config/claim_reconciliation_map_v0_1.json",
    "knowledge_base": ROOT / "data/BioSafe_Knowledge_Base_v0.2.json",
    "source_policy": INGESTION / "config/source_policy_v0_1.json",
    "source_register": ROOT / "controlled_sources/staging_v0_1/SOURCE_REGISTER.tsv",
    "component_artifact": INGESTION / "reports/component_candidates_v0_1.json",
    "fallback_artifact": INGESTION / "reports/semantic_fallbacks_v0_1.json",
    "fallback_review_packet": INGESTION / "reports/fallback_human_review_packet_v0_1.json",
}


class ClaimReviewAidTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = {name: path.read_bytes() for name, path in PATHS.items()}
        cls.data = {
            name: (
                list(csv.DictReader(io.StringIO(value.decode("utf-8")), delimiter="\t"))
                if name == "source_register" else json.loads(value)
            )
            for name, value in cls.raw.items()
        }
        cls.aid = cls._build()

    @classmethod
    def _build(cls, **changes):
        data = dict(cls.data)
        data.update(changes)
        return build_claim_review_aid(
            data["crosswalk"], cls.raw["crosswalk"], data["review_map"], cls.raw["review_map"],
            data["knowledge_base"], cls.raw["knowledge_base"],
            data["source_policy"], cls.raw["source_policy"],
            data["source_register"], cls.raw["source_register"],
            data["component_artifact"], cls.raw["component_artifact"],
            data["fallback_artifact"], cls.raw["fallback_artifact"],
            data["fallback_review_packet"], cls.raw["fallback_review_packet"],
        )

    def test_aid_is_navigation_only_offline_and_covers_all_pending_work(self):
        self.assertEqual(self.aid["aid_scope"], NO_AUTOMATED_DISPOSITION)
        self.assertEqual(self.aid["identity_mapping_item_count"], 4)
        self.assertEqual(self.aid["completed_identity_review_count"], 4)
        self.assertEqual(self.aid["pending_identity_review_count"], 0)
        self.assertEqual(self.aid["claim_review_item_count"], 45)
        completed_count = len(LEGAL_CLAIM_IDS | COMPLETED_NONLEGAL_CLAIM_IDS)
        self.assertEqual(self.aid["completed_claim_review_count"], completed_count)
        self.assertEqual(self.aid["pending_claim_review_count"], 45 - completed_count)
        self.assertEqual(self.aid["claim_use_status"], CLAIM_REVIEW_REQUIRED)
        self.assertEqual(self.aid["live_activation_status"], ACTIVATION_PROHIBITED)
        for item in self.aid["identity_mapping_items"]:
            self.assertIsNone(item["automated_disposition"])
        for item in self.aid["claim_review_items"]:
            self.assertEqual(item["automated_atomic_propositions"], [])
            self.assertIsNone(item["automated_disposition"])
            self.assertIsNone(item["reviewer_identity"])
            self.assertIsNone(item["reviewer_attestations"])

    def test_unambiguous_legacy_ranges_are_navigation_hints_not_decisions(self):
        by_id = {item["claim_id"]: item for item in self.aid["claim_review_items"]}
        self.assertEqual(by_id["CLM-001"]["page_hint"], {
            "pdf_page_start": 90, "pdf_page_end": 91,
            "basis": "LEGACY_PAGE_FIELD_NAVIGATION_ONLY",
        })
        self.assertTrue(by_id["CLM-001"]["native_candidate_suggestions"])
        self.assertIsNone(by_id["CLM-032"]["page_hint"])
        self.assertTrue(by_id["CLM-032"]["manual_navigation_required"])
        self.assertEqual(by_id["CLM-032"]["native_candidate_suggestions"], [])

    def test_completed_alias_identity_is_visible_on_dependent_claims(self):
        by_id = {item["claim_id"]: item for item in self.aid["claim_review_items"]}
        completed_alias_claims = (
            LEGAL_CLAIM_IDS & {"CLM-026", "CLM-029", "CLM-042", "CLM-045"}
        ) | {"CLM-045"}
        for claim_id in completed_alias_claims:
            self.assertEqual(by_id[claim_id]["identity_review_status"], "HUMAN_IDENTITY_REVIEW_COMPLETE")
            self.assertEqual(by_id[claim_id]["claim_review_status"], CLAIM_REVIEW_COMPLETE)
        for claim_id in (
            {"CLM-043", "CLM-029", "CLM-042", "CLM-045"}
            - LEGAL_CLAIM_IDS - completed_alias_claims
        ):
            self.assertEqual(by_id[claim_id]["identity_review_status"], "HUMAN_IDENTITY_REVIEW_COMPLETE")
            self.assertEqual(by_id[claim_id]["claim_review_status"], CLAIM_REVIEW_REQUIRED)

    def test_identity_items_include_hash_bound_register_and_front_matter_evidence(self):
        for item in self.aid["identity_mapping_items"]:
            self.assertEqual(
                item["controlled_source_register_record"]["sha256"],
                item["controlled_source_sha256"],
            )
            self.assertEqual(len(item["controlled_front_matter_candidates"]), 3)
            self.assertTrue(all(
                candidate["source_sha256"] == item["controlled_source_sha256"]
                for candidate in item["controlled_front_matter_candidates"]
            ))
            review = item["identity_review_record"]
            self.assertEqual(review["reviewer_identity"], "BioSafe project owner")
            self.assertEqual(review["review_date"], "2026-09-10")

    def test_identity_register_hash_drift_fails_closed(self):
        changed = json.loads(json.dumps(self.data["source_register"]))
        record = next(item for item in changed if item["candidate_id"] == "KB-MY-SW2005")
        record["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValidationError, "register hash mismatch"):
            self._build(source_register=changed)

    def test_boundary_prompts_distinguish_law_form_waste_transport_and_who(self):
        by_id = {item["claim_id"]: item for item in self.aid["claim_review_items"]}
        self.assertTrue(any("not an approval" in text for text in by_id["CLM-018"]["boundary_prompts"]))
        self.assertTrue(any("not automatically SW 404" in text for text in by_id["CLM-029"]["boundary_prompts"]))
        self.assertTrue(any("does not establish laboratory containment" in text for text in by_id["CLM-026"]["boundary_prompts"]))
        self.assertTrue(any("not Malaysian law" in text for text in by_id["CLM-042"]["boundary_prompts"]))

    def test_excluded_native_pages_are_reported_and_never_suggested_as_native(self):
        changed = json.loads(json.dumps(self.data["review_map"]))
        review = next(item for item in changed["claim_reviews"] if item["claim_id"] == "CLM-029")
        review["original_claim"]["page"] = "18–23"
        kb = json.loads(json.dumps(self.data["knowledge_base"]))
        next(item for item in kb["claims"] if item["claim_id"] == "CLM-029")["page"] = "18–23"
        aid = self._build(review_map=changed, knowledge_base=kb)
        item = next(item for item in aid["claim_review_items"] if item["claim_id"] == "CLM-029")
        self.assertEqual(item["excluded_native_pages_in_hint"], [18, 19, 20, 21, 22, 23])
        self.assertEqual(item["native_candidate_suggestions"], [])
        self.assertEqual(len(item["reviewed_fallback_suggestions"]), 6)

    def test_tampered_or_incomplete_review_map_fails_closed(self):
        changed = json.loads(json.dumps(self.data["review_map"]))
        changed["claim_reviews"].pop()
        with self.assertRaisesRegex(ValidationError, "exact knowledge-base claim set"):
            self._build(review_map=changed)
        changed = json.loads(json.dumps(self.data["review_map"]))
        changed["claim_reviews"][0]["controlled_source_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValidationError, "identity binding mismatch"):
            self._build(review_map=changed)

    def test_serialization_is_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "aid.json"
            write_claim_review_aid(self.aid, output)
            first = output.read_bytes()
            write_claim_review_aid(self.aid, output)
            self.assertEqual(first, output.read_bytes())

    def test_public_builder_cli_accepts_tsv_register_and_writes_aid(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "aid.json"
            environment = dict(os.environ)
            environment["PYTHONPATH"] = str(SRC)
            result = subprocess.run(
                [
                    sys.executable,
                    str(INGESTION / "scripts/build_claim_review_aid.py"),
                    "--crosswalk", str(PATHS["crosswalk"]),
                    "--review-map", str(PATHS["review_map"]),
                    "--knowledge-base", str(PATHS["knowledge_base"]),
                    "--source-policy", str(PATHS["source_policy"]),
                    "--source-register", str(PATHS["source_register"]),
                    "--component-artifact", str(PATHS["component_artifact"]),
                    "--fallback-artifact", str(PATHS["fallback_artifact"]),
                    "--fallback-review-packet", str(PATHS["fallback_review_packet"]),
                    "--output", str(output),
                ],
                capture_output=True,
                text=True,
                env=environment,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("identity_mappings=4 identity_pending=0 claim_reviews=45", result.stdout)
            self.assertEqual(json.loads(output.read_bytes()), self.aid)


class RegulationsIdentifierMetadataTests(unittest.TestCase):
    def test_register_identifier_matches_controlled_source_and_component_boundary(self):
        with (ROOT / "controlled_sources/staging_v0_1/SOURCE_REGISTER.tsv").open(
            newline="", encoding="utf-8"
        ) as handle:
            record = next(row for row in csv.DictReader(handle, delimiter="\t") if row["candidate_id"] == "KB-MY-REG2010")
        pages = json.loads((INGESTION / "reports/all_sources_pages_v0_1.json").read_text(encoding="utf-8"))
        document = next(item for item in pages["documents"] if item["document_id"] == "KB-MY-REG2010")
        first_page = document["pages"][0]["text"]
        components = json.loads((INGESTION / "reports/component_candidates_v0_1.json").read_text(encoding="utf-8"))
        component = next(item for item in components["components"] if item["component_id"] == "KB-MY-REG2010:PUA367")
        text = "\n".join(page["text"] for page in component["pages"])
        self.assertEqual(record["identifier"], "P.U. (A) 367/2010")
        self.assertIn("P.U. (A) 367.", first_page)
        self.assertNotIn("P.U. (A) 368.", text)


if __name__ == "__main__":
    unittest.main()