from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
INGESTION = ROOT / "controlled_sources/ingestion_v0_1"
SRC = INGESTION / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from biosafe_controlled_ingestion.components import (  # noqa: E402
    ACTIVATION_PROHIBITED,
    CLAIM_REVIEW_REQUIRED,
)
from biosafe_controlled_ingestion.contracts import ValidationError  # noqa: E402
from biosafe_controlled_ingestion.fallback_human_review import (  # noqa: E402
    ALLOWED_DISPOSITIONS,
    HUMAN_REVIEW_COMPLETE,
    HUMAN_REVIEW_REQUIRED,
    build_fallback_human_review_packet,
    write_fallback_human_review_packet,
)


REVIEW_MAP = INGESTION / "config/fallback_human_review_map_v0_1.json"
FALLBACKS = INGESTION / "reports/semantic_fallbacks_v0_1.json"
RENDERS = INGESTION / "reports/targeted_visual_review_v0_1/RENDER_MANIFEST.json"


class FallbackHumanReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.review_map = json.loads(REVIEW_MAP.read_text(encoding="utf-8"))
        cls.fallback_bytes = FALLBACKS.read_bytes()
        cls.fallbacks = json.loads(cls.fallback_bytes)
        cls.renders = json.loads(RENDERS.read_text(encoding="utf-8"))
        cls.packet = build_fallback_human_review_packet(
            cls.review_map, cls.fallbacks, cls.fallback_bytes, cls.renders
        )

    def test_packet_covers_exactly_twelve_fallback_units_and_is_hash_bound(self):
        self.assertEqual(self.packet["required_review_count"], 12)
        self.assertEqual(self.packet["completed_review_count"], 12)
        self.assertEqual(
            self.packet["source_fallback_artifact_sha256"],
            hashlib.sha256(self.fallback_bytes).hexdigest(),
        )
        self.assertEqual(
            {item["fallback_unit_id"] for item in self.packet["review_items"]},
            {unit["fallback_unit_id"] for unit in self.fallbacks["fallback_units"]},
        )

    def test_all_reviews_are_accepted_with_claim_use_and_activation_still_gated(self):
        self.assertEqual(self.packet["review_completion_status"], HUMAN_REVIEW_COMPLETE)
        self.assertEqual(
            self.packet["review_gate_status"],
            "TRANSCRIPTION_REVIEW_ACCEPTED_CLAIM_REVIEW_REQUIRED",
        )
        self.assertEqual(self.packet["review_scope"], "TRANSCRIPTION_AND_REPRESENTATION_ONLY")
        self.assertEqual(self.packet["claim_use_status"], CLAIM_REVIEW_REQUIRED)
        self.assertEqual(self.packet["live_activation_status"], ACTIVATION_PROHIBITED)
        completed = [
            item for item in self.packet["review_items"]
            if item["review_record"]["review_status"] == HUMAN_REVIEW_COMPLETE
        ]
        pending = [
            item for item in self.packet["review_items"]
            if item["review_record"]["review_status"] == HUMAN_REVIEW_REQUIRED
        ]
        self.assertEqual(len(completed), 12)
        self.assertEqual(pending, [])
        accepted = [
            item for item in completed
            if item["review_record"]["disposition"] == "ACCEPT_AS_TRANSCRIBED"
        ]
        self.assertEqual(len(accepted), 12)
        self.assertEqual(
            {item["document_id"] for item in accepted},
            {
                "KB-WHO-LBM4-PROG",
                "KB-MY-GMMRA",
                "KB-WHO-LBM4-DESIGN",
                "KB-WHO-LBM4-PPE",
                "KB-MY-SW2005",
            },
        )
        for item in accepted:
            review = item["review_record"]
            self.assertEqual(review["disposition"], "ACCEPT_AS_TRANSCRIBED")
            self.assertEqual(review["reviewer_identity"], "BioSafe project owner")
            self.assertEqual(review["reviewer_role"], "Source transcription reviewer")
            self.assertEqual(review["review_date"], "2026-09-09")
            self.assertTrue(all(value == "PASS" for value in review["check_results"].values()))
            self.assertTrue(all(value is True for value in review["attestations"].values()))
        for item in completed:
            self.assertTrue(item["review_record"]["findings"])
            self.assertEqual(item["claim_use_status"], CLAIM_REVIEW_REQUIRED)
            self.assertEqual(item["live_activation_status"], ACTIVATION_PROHIBITED)

    def test_checklists_are_source_specific_and_cover_high_risk_boundaries(self):
        by_page = {
            (item["document_id"], item["pdf_page_index"]): item
            for item in self.packet["review_items"]
        }
        expected = {
            ("KB-WHO-LBM4-PROG", 56): {"stage_and_column_order", "row_group_labels", "cell_associations"},
            ("KB-MY-GMMRA", 42): {"matrix_cell_product", "likelihood_key", "interpretation_qualifiers"},
            ("KB-MY-GMMRA", 175): {"matrix_title_axes_and_cells", "source_context", "likelihood_key_absence"},
            ("KB-WHO-LBM4-DESIGN", 55): {"approval_branches", "revision_loops", "bypass_and_terminals"},
            ("KB-WHO-LBM4-DESIGN", 71): {"three_maintenance_paths", "downstream_sequence", "no_invented_decisions"},
            ("KB-WHO-LBM4-PPE", 42): {"frame_count_and_order", "no_textual_step_labels", "no_inferred_instructions"},
            ("KB-MY-SW2005", 18): {"symbols_and_colors", "printed_label_numbers", "excluded_inferences"},
            ("KB-MY-SW2005", 19): {"cross_page_label_2", "rendered_glyph_observations", "glyph_text_discrepancies"},
            ("KB-MY-SW2005", 23): {"label_requirements", "rendered_glyph_observations", "glyph_text_discrepancies"},
        }
        for page_key, required in expected.items():
            observed = {check["check_id"] for check in by_page[page_key]["required_checks"]}
            self.assertTrue(required <= observed)

    def test_source_hash_unknown_unit_or_incomplete_coverage_fails_closed(self):
        bad_hash = json.loads(json.dumps(self.review_map))
        bad_hash["source_fallback_artifact_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValidationError, "canonical bytes"):
            build_fallback_human_review_packet(
                bad_hash, self.fallbacks, self.fallback_bytes, self.renders
            )

        mismatched_object = json.loads(json.dumps(self.fallbacks))
        mismatched_object["fallback_units"][0]["pdf_page_label"] = "changed"
        with self.assertRaisesRegex(ValidationError, "hash-bound bytes"):
            build_fallback_human_review_packet(
                self.review_map, mismatched_object, self.fallback_bytes, self.renders
            )

        bad_render = json.loads(json.dumps(self.renders))
        unit = self.fallbacks["fallback_units"][0]
        render = next(
            item for item in bad_render["renders"]
            if item["document_id"] == unit["document_id"]
            and item["pdf_page_index"] == unit["pdf_page_index"]
        )
        render["rendered_filename"] = "changed.png"
        with self.assertRaisesRegex(ValidationError, "render provenance"):
            build_fallback_human_review_packet(
                self.review_map, self.fallbacks, self.fallback_bytes, bad_render
            )

        unknown = json.loads(json.dumps(self.review_map))
        unknown["review_items"][0]["fallback_unit_id"] = "UNKNOWN"
        with self.assertRaisesRegex(ValidationError, "unknown fallback unit"):
            build_fallback_human_review_packet(
                unknown, self.fallbacks, self.fallback_bytes, self.renders
            )

        incomplete = json.loads(json.dumps(self.review_map))
        incomplete["review_items"].pop()
        with self.assertRaisesRegex(ValidationError, "every fallback unit"):
            build_fallback_human_review_packet(
                incomplete, self.fallbacks, self.fallback_bytes, self.renders
            )

    def test_partial_or_falsely_completed_review_fails_closed(self):
        partial = json.loads(json.dumps(self.review_map))
        review = partial["review_items"][2]["review_record"]
        review.update({
            "review_status": HUMAN_REVIEW_REQUIRED,
            "disposition": None,
            "reviewer_identity": "Someone",
            "reviewer_role": None,
            "review_date": None,
            "findings": [],
        })
        review["check_results"] = {key: None for key in review["check_results"]}
        review["attestations"] = {key: False for key in review["attestations"]}
        with self.assertRaisesRegex(ValidationError, "must be null"):
            build_fallback_human_review_packet(
                partial, self.fallbacks, self.fallback_bytes, self.renders
            )

        false_complete = json.loads(json.dumps(self.review_map))
        review = false_complete["review_items"][2]["review_record"]
        review.update({
            "review_status": HUMAN_REVIEW_COMPLETE,
            "disposition": "ACCEPT_AS_TRANSCRIBED",
            "reviewer_identity": None,
            "reviewer_role": None,
            "review_date": None,
            "findings": [],
        })
        with self.assertRaisesRegex(ValidationError, "reviewer_identity"):
            build_fallback_human_review_packet(
                false_complete, self.fallbacks, self.fallback_bytes, self.renders
            )

    def test_completed_dispositions_require_consistent_evidence(self):
        for disposition in sorted(ALLOWED_DISPOSITIONS):
            changed = json.loads(json.dumps(self.review_map))
            review = changed["review_items"][2]["review_record"]
            review.update({
                "review_status": HUMAN_REVIEW_COMPLETE,
                "disposition": disposition,
                "reviewer_identity": "Independent reviewer",
                "reviewer_role": "Source comparison reviewer",
                "review_date": "2026-09-09",
                "findings": ["Source comparison result recorded for contract testing."],
            })
            result = {
                "ACCEPT_AS_TRANSCRIBED": "PASS",
                "CORRECTION_REQUIRED": "FAIL",
                "REJECT_REPRESENTATION": "FAIL",
                "UNRESOLVED_SOURCE_AMBIGUITY": "AMBIGUOUS",
            }[disposition]
            review["check_results"] = {key: result for key in review["check_results"]}
            review["attestations"] = {key: True for key in review["attestations"]}
            packet = build_fallback_human_review_packet(
                changed, self.fallbacks, self.fallback_bytes, self.renders
            )
            self.assertEqual(
                packet["completed_review_count"],
                self.packet["completed_review_count"],
            )
            self.assertEqual(packet["claim_use_status"], CLAIM_REVIEW_REQUIRED)
            self.assertEqual(packet["live_activation_status"], ACTIVATION_PROHIBITED)

        inconsistent = json.loads(json.dumps(changed))
        review = inconsistent["review_items"][2]["review_record"]
        review["disposition"] = "ACCEPT_AS_TRANSCRIBED"
        with self.assertRaisesRegex(ValidationError, "every human review check to pass"):
            build_fallback_human_review_packet(
                inconsistent, self.fallbacks, self.fallback_bytes, self.renders
            )

    def test_aggregate_gate_status_fails_closed_by_disposition(self):
        expected = {
            "REJECT_REPRESENTATION": "BLOCKED_REPRESENTATION_REJECTED",
            "CORRECTION_REQUIRED": "BLOCKED_CORRECTION_REQUIRED",
            "UNRESOLVED_SOURCE_AMBIGUITY": "BLOCKED_UNRESOLVED_SOURCE_AMBIGUITY",
            "ACCEPT_AS_TRANSCRIBED": "TRANSCRIPTION_REVIEW_ACCEPTED_CLAIM_REVIEW_REQUIRED",
        }
        for disposition, gate_status in expected.items():
            changed = json.loads(json.dumps(self.review_map))
            for item in changed["review_items"]:
                review = item["review_record"]
                if review["review_status"] == HUMAN_REVIEW_REQUIRED:
                    review.update({
                        "review_status": HUMAN_REVIEW_COMPLETE,
                        "disposition": "ACCEPT_AS_TRANSCRIBED",
                        "reviewer_identity": "Synthetic contract-test reviewer",
                        "reviewer_role": "Source comparison test fixture",
                        "review_date": "2026-09-09",
                        "findings": ["Synthetic complete record for aggregate contract testing."],
                    })
                    review["check_results"] = {key: "PASS" for key in review["check_results"]}
                    review["attestations"] = {key: True for key in review["attestations"]}
            review = changed["review_items"][2]["review_record"]
            review.update({
                "review_status": HUMAN_REVIEW_COMPLETE,
                "disposition": disposition,
                "reviewer_identity": "Independent reviewer",
                "reviewer_role": "Source comparison reviewer",
                "review_date": "2026-09-09",
                "findings": ["Source comparison result recorded for contract testing."],
            })
            review["attestations"] = {key: True for key in review["attestations"]}
            result = {
                "REJECT_REPRESENTATION": "FAIL",
                "CORRECTION_REQUIRED": "FAIL",
                "UNRESOLVED_SOURCE_AMBIGUITY": "AMBIGUOUS",
                "ACCEPT_AS_TRANSCRIBED": "PASS",
            }[disposition]
            review["check_results"] = {
                key: result for key in review["check_results"]
            }
            packet = build_fallback_human_review_packet(
                changed, self.fallbacks, self.fallback_bytes, self.renders
            )
            self.assertEqual(packet["review_gate_status"], gate_status)
            self.assertEqual(packet["claim_use_status"], CLAIM_REVIEW_REQUIRED)
            self.assertEqual(packet["live_activation_status"], ACTIVATION_PROHIBITED)

    def test_serialization_is_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "review_packet.json"
            write_fallback_human_review_packet(self.packet, output)
            first = output.read_bytes()
            write_fallback_human_review_packet(self.packet, output)
            self.assertEqual(first, output.read_bytes())


if __name__ == "__main__":
    unittest.main()