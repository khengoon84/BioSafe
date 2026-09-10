from __future__ import annotations

import json
import sys
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
    ComponentPolicy,
    ComponentSpan,
    build_component_artifact,
    build_review_ledger,
    load_component_map,
)
from biosafe_controlled_ingestion.contracts import ValidationError  # noqa: E402


COMPONENT_MAP = INGESTION / "config/component_map_v0_1.json"
PAGES = INGESTION / "reports/all_sources_pages_v0_1.json"
VISUAL_SELECTION = INGESTION / "config/targeted_visual_review_pages_v0_1.json"


def fixture_report(text: str = "retained END excluded") -> dict:
    return {
        "report_version": "test",
        "documents": [{
            "document_id": "D1", "source_sha256": "a" * 64,
            "pages": [{
                "pdf_page_index": 1, "pdf_page_label": "i", "printed_page_label": "",
                "text": text, "extraction_method": "test", "extraction_warnings": [],
            }],
        }],
    }


def fixture_policy(**changes) -> ComponentPolicy:
    values = {
        "component_id": "D1:C1", "document_id": "D1", "source_sha256": "a" * 64,
        "title": "Component", "component_type": "test",
        "spans": (ComponentSpan(1, 1, end_before="END"),),
        "allowed_domains": ("allowed",), "excluded_domains": ("excluded",),
        "review_status": "TEST_REVIEWED",
    }
    values.update(changes)
    return ComponentPolicy(**values)


class ComponentUnitTests(unittest.TestCase):
    def test_unique_end_marker_is_excluded(self):
        artifact = build_component_artifact(fixture_report(), (fixture_policy(),))
        self.assertEqual(artifact["components"][0]["pages"][0]["text"], "retained")
        self.assertEqual(artifact["candidate_chunks"][0]["text"], "retained")
        self.assertEqual(artifact["claim_use_status"], CLAIM_REVIEW_REQUIRED)
        self.assertEqual(artifact["live_activation_status"], ACTIVATION_PROHIBITED)

    def test_unmarked_empty_page_is_retained_but_not_chunked(self):
        policy = fixture_policy(spans=(ComponentSpan(1, 1),))
        artifact = build_component_artifact(fixture_report(""), (policy,))
        self.assertEqual(artifact["components"][0]["page_record_count"], 1)
        self.assertEqual(artifact["components"][0]["pages"][0]["text"], "")
        self.assertEqual(artifact["candidate_chunks"], [])

    def test_missing_or_duplicate_boundary_marker_fails_closed(self):
        with self.assertRaisesRegex(ValidationError, "end marker count is 0"):
            build_component_artifact(fixture_report("no boundary"), (fixture_policy(),))
        with self.assertRaisesRegex(ValidationError, "end marker count is 2"):
            build_component_artifact(fixture_report("END END"), (fixture_policy(),))

    def test_source_hash_mismatch_fails_closed(self):
        with self.assertRaisesRegex(ValidationError, "source hash mismatch"):
            build_component_artifact(fixture_report(), (fixture_policy(source_sha256="b" * 64),))

    def test_domain_overlap_is_rejected(self):
        policy = fixture_policy(allowed_domains=("same",), excluded_domains=("same",))
        with self.assertRaisesRegex(ValidationError, "must not overlap"):
            policy.validate(1)

    def test_candidate_exclusion_outside_component_is_rejected(self):
        policy = fixture_policy(candidate_excluded_pages=(2,))
        with self.assertRaisesRegex(ValidationError, "outside its spans"):
            policy.validate(1)

    def test_owner_confirmed_blanks_replace_empty_warning_review(self):
        report = fixture_report("")
        report["documents"][0]["pages"][0]["extraction_warnings"] = [
            "PAGE_TEXT_EMPTY_POSSIBLE_SCAN_OR_DECORATIVE_PAGE"
        ]
        component_map = {"fixed_review_dispositions": [{
            "document_id": "D1", "pdf_page_start": 1, "pdf_page_end": 1,
            "disposition": "CONFIRMED_BLANK", "review_basis": "OWNER", "notes": "blank",
        }]}
        rows = build_review_ledger(report, component_map)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["disposition"], "CONFIRMED_BLANK")


@unittest.skipUnless(PAGES.exists(), "full extraction report is not present")
class ActualArtifactBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.component_map, policies = load_component_map(COMPONENT_MAP)
        cls.report = json.loads(PAGES.read_text(encoding="utf-8"))
        cls.artifact = build_component_artifact(cls.report, policies)
        cls.by_id = {item["component_id"]: item for item in cls.artifact["components"]}

    def test_regulations_component_excludes_other_gazette_instruments(self):
        component = self.by_id["KB-MY-REG2010:PUA367"]
        text = "\n".join(page["text"] for page in component["pages"])
        self.assertEqual(component["page_record_count"], 35)
        self.assertIn("Made 25 October 2010", text)
        self.assertIn("DATO SRI DOUGLAS UGGAH EMBAS", text)
        for prohibited in (
            "P.U. (A) 368.", "AKTA KASTAM 1967", "CUSTOMS ACT 1967",
            "P.U. (A) 369.", "P.U. (A) 370.", "P.U. (A) 371.", "P.U. (A) 372.",
        ):
            self.assertNotIn(prohibited, text)
        page_35 = component["pages"][-1]
        self.assertEqual(page_35["boundary_positions"]["end_before_character"], 4278)

    def test_all_form_bundle_pages_are_retained_once(self):
        form_components = [item for item in self.artifact["components"] if item["document_id"] == "KB-MY-FORME"]
        pages = [page["pdf_page_index"] for item in form_components for page in item["pages"]]
        self.assertEqual(pages, list(range(1, 222)))
        self.assertEqual(len(set(pages)), 221)
        self.assertEqual(len(form_components), 10)

    def test_form_e_and_form_f_scopes_cannot_cross(self):
        form_e = self.by_id["KB-MY-FORME:FORM_E_APPLICANT_PART_A"]
        form_f = self.by_id["KB-MY-FORME:FORM_F"]
        self.assertIn("form_e_researcher_assistance", form_e["allowed_domains"])
        self.assertIn("form_f_export_notification", form_e["excluded_domains"])
        self.assertIn("form_f_export_notification", form_f["allowed_domains"])
        self.assertIn("form_e_researcher_assistance", form_f["excluded_domains"])
        self.assertTrue(all(210 <= page["pdf_page_index"] <= 215 for page in form_e["pages"]))
        self.assertTrue(all(216 <= page["pdf_page_index"] <= 220 for page in form_f["pages"]))

    def test_form_e_ibc_assessment_is_not_researcher_facing(self):
        ibc = self.by_id["KB-MY-FORME:FORM_E_IBC_ASSESSMENT"]
        applicant = self.by_id["KB-MY-FORME:FORM_E_APPLICANT_PART_A"]
        self.assertEqual([page["pdf_page_index"] for page in ibc["pages"]], [208, 209])
        self.assertIn("ibc_assessment", ibc["allowed_domains"])
        self.assertIn("form_e_researcher_assistance", ibc["excluded_domains"])
        self.assertIn("form_e_researcher_assistance", applicant["allowed_domains"])
        self.assertIn("ibc_assessment", applicant["excluded_domains"])

    def test_candidates_are_never_live_or_claim_approved(self):
        self.assertTrue(self.artifact["candidate_chunks"])
        for chunk in self.artifact["candidate_chunks"]:
            self.assertEqual(chunk["live_activation_status"], ACTIVATION_PROHIBITED)
            self.assertEqual(chunk["claim_use_status"], CLAIM_REVIEW_REQUIRED)

    def test_act_owner_confirmed_blank_dispositions_exist(self):
        rows = build_review_ledger(self.report, self.component_map)
        blanks = {
            int(row["pdf_page_index"]) for row in rows
            if row["document_id"] == "KB-MY-ACT678" and row["disposition"] == "CONFIRMED_BLANK"
        }
        self.assertEqual(blanks, {62})
        conflicts = {
            int(row["pdf_page_index"]) for row in rows
            if row["document_id"] == "KB-MY-ACT678"
            and row["disposition"] == "OCR_REQUIRED_OWNER_CLASSIFICATION_CONFLICT"
        }
        self.assertEqual(conflicts, {64})

    def test_act_candidates_exclude_only_owner_confirmed_blank_pages(self):
        act = self.by_id["KB-MY-ACT678:SELECTED_LOCAL_ACT_TEXT"]
        pages = [page["pdf_page_index"] for page in act["pages"]]
        self.assertEqual(pages, [page for page in range(1, 119) if page != 62])
        self.assertEqual(act["source_sha256"], "8c2badc2db503906b92a42b905736653b868ee3c7bc6fb79719e0081cf25e8cc")
        self.assertEqual(
            act["review_status"],
            "OWNER_DESIGNATED_SOLE_CANONICAL_SOURCE_AMENDMENT_AND_CLAIM_REVIEW_REQUIRED",
        )
        self.assertNotIn("VARIANT_CONFLICT", act["review_status"])
        self.assertEqual(act["live_activation_status"], ACTIVATION_PROHIBITED)

    def test_act_page_64_is_retained_but_not_a_text_candidate(self):
        act = self.by_id["KB-MY-ACT678:SELECTED_LOCAL_ACT_TEXT"]
        page_64 = next(page for page in act["pages"] if page["pdf_page_index"] == 64)
        self.assertEqual(page_64["text"], "")
        chunk_pages = {
            chunk["pdf_page_start"] for chunk in self.artifact["candidate_chunks"]
            if chunk["component_id"] == act["component_id"]
        }
        self.assertNotIn(64, chunk_pages)

    def test_all_extraction_empty_warnings_have_visual_dispositions(self):
        rows = build_review_ledger(self.report, self.component_map)
        empty_rows = [
            row for row in rows
            if row["warning"] == "PAGE_TEXT_EMPTY_POSSIBLE_SCAN_OR_DECORATIVE_PAGE"
        ]
        self.assertEqual(len(empty_rows), 23)
        self.assertFalse(any(row["disposition"] == "REVIEW_PENDING" for row in empty_rows))
        blank_pages = {
            (row["document_id"], int(row["pdf_page_index"])) for row in empty_rows
            if row["disposition"] == "CONFIRMED_BLANK_SOURCE_BOUND_RENDER"
        }
        decorative_pages = {
            (row["document_id"], int(row["pdf_page_index"])) for row in empty_rows
            if row["disposition"] == "ACCEPT_EMPTY_DECORATIVE_OR_PUBLISHER_ARTWORK"
        }
        self.assertEqual(len(blank_pages), 13)
        self.assertEqual(len(decorative_pages), 10)
        candidate_pages = {
            (chunk["document_id"], chunk["pdf_page_start"])
            for chunk in self.artifact["candidate_chunks"]
        }
        self.assertFalse((blank_pages | decorative_pages) & candidate_pages)

    def test_all_low_volume_warnings_have_visual_dispositions(self):
        rows = build_review_ledger(self.report, self.component_map)
        low_volume_rows = [
            row for row in rows
            if row["warning"] == "PAGE_TEXT_LOW_VOLUME_REVIEW_REQUIRED"
        ]
        self.assertEqual(len(low_volume_rows), 80)
        self.assertFalse(any(row["disposition"] == "REVIEW_PENDING" for row in low_volume_rows))
        accepted = [
            row for row in low_volume_rows
            if row["disposition"]
            == "ACCEPT_LOW_VOLUME_TEXT_SOURCE_BOUND_VISUAL_REVIEW_CLAIM_REVIEW_REQUIRED"
        ]
        fallback_pages = {
            (row["document_id"], int(row["pdf_page_index"])) for row in low_volume_rows
            if row["disposition"] == "FALLBACK_REQUIRED_SUBSTANTIVE_GRAPHICAL_CONTENT"
        }
        self.assertEqual(len(accepted), 78)
        self.assertEqual(fallback_pages, {("KB-MY-FORME", 26), ("KB-WHO-LBM4-PPE", 42)})
        candidate_pages = {
            (chunk["document_id"], chunk["pdf_page_start"])
            for chunk in self.artifact["candidate_chunks"]
        }
        self.assertFalse(fallback_pages & candidate_pages)

    def test_scheduled_waste_components_cover_every_page_without_text_overlap(self):
        components = [
            item for item in self.artifact["components"] if item["document_id"] == "KB-MY-SW2005"
        ]
        self.assertEqual(len(components), 9)
        pages = {page["pdf_page_index"] for item in components for page in item["pages"]}
        self.assertEqual(pages, set(range(1, 35)))
        intervals: dict[int, list[tuple[int, int]]] = {}
        for component in components:
            for page in component["pages"]:
                bounds = page["boundary_positions"]
                interval = (bounds["selected_character_start"], bounds["selected_character_end"])
                for existing in intervals.get(page["pdf_page_index"], []):
                    self.assertGreaterEqual(max(interval[0], existing[0]), min(interval[1], existing[1]))
                intervals.setdefault(page["pdf_page_index"], []).append(interval)

    def test_all_scheduled_waste_symbolset_warnings_have_visual_dispositions(self):
        rows = build_review_ledger(self.report, self.component_map)
        symbolset_rows = [
            row for row in rows
            if row["document_id"] == "KB-MY-SW2005"
            and row["warning"] == "FONT_ENCODING_SYMBOLSET_UNSUPPORTED"
        ]
        self.assertEqual(len(symbolset_rows), 34)
        self.assertFalse(any(row["disposition"] == "REVIEW_PENDING" for row in symbolset_rows))
        accepted_pages = {
            int(row["pdf_page_index"]) for row in symbolset_rows
            if row["disposition"]
            == "ACCEPT_TEXT_TARGETED_VISUAL_MATCH_CLAIM_REVIEW_REQUIRED"
        }
        fallback_pages = {
            int(row["pdf_page_index"]) for row in symbolset_rows
            if row["disposition"] == "FALLBACK_REQUIRED_FOR_GRAPHICAL_LABEL_CONTENT"
        }
        self.assertEqual(accepted_pages, set(range(1, 35)) - set(range(18, 24)))
        self.assertEqual(fallback_pages, set(range(18, 24)))

    def test_all_scheduled_waste_pages_are_persistently_selected_for_visual_review(self):
        selection = json.loads(VISUAL_SELECTION.read_text(encoding="utf-8"))
        self.assertEqual(selection["KB-MY-SW2005"], list(range(1, 35)))

    def test_rotated_layout_warning_partition_is_exact(self):
        rows = build_review_ledger(self.report, self.component_map)
        rotated = [
            row for row in rows
            if row["warning"] == "ROTATED_TEXT_OMITTED_BY_LAYOUT_MODE"
            and not (
                row["document_id"] == "KB-MY-FORME"
                or (row["document_id"] == "KB-WHO-LBM4-DECON" and row["pdf_page_index"] == "15")
            )
        ]
        accepted = {
            (row["document_id"], int(row["pdf_page_index"])) for row in rotated
            if row["disposition"] == "ACCEPT_NATIVE_TEXT_ROTATED_TEMPLATE_LABEL_NONMATERIAL"
        }
        fallback = {
            (row["document_id"], int(row["pdf_page_index"])) for row in rotated
            if row["disposition"] == "FALLBACK_REQUIRED_SUBSTANTIVE_ROTATED_STRUCTURE"
        }
        pending = {
            (row["document_id"], int(row["pdf_page_index"])) for row in rotated
            if row["disposition"] == "REVIEW_PENDING"
        }
        self.assertEqual(accepted, {
            ("KB-MY-CU", 1),
            *{("KB-WHO-LBM4", page) for page in (21, 25, 47, 69, 79)},
            *{("KB-WHO-LBM4-BSC", page) for page in (13, 17, 21, 27)},
            *{("KB-WHO-LBM4-DECON", page) for page in (13, 37, 49)},
            *{("KB-WHO-LBM4-DESIGN", page) for page in (19, 21, 29, 37, 43, 45, 63, 79)},
            *{("KB-WHO-LBM4-OUTBREAK", page) for page in (15, 27, 31, 35, 37, 53, 59, 61, 67, 69)},
            *{("KB-WHO-LBM4-PPE", page) for page in (17, 21, 29, 33, 37, 39, 45, 47, 53, 55, 71)},
            *{("KB-WHO-LBM4", page) for page in (85, 97, 103, 111)},
            *{("KB-WHO-LBM4-PPE", page) for page in (73, 75, 81)},
            *{("KB-WHO-LBM4-PROG", page) for page in (17, 19, 21, 23, 27)},
            *{("KB-WHO-LBM4-RA", page) for page in (15, 19, 27, 28, 39)},
        })
        self.assertEqual(fallback, {
            ("KB-MY-GMMRA", 42), ("KB-MY-GMMRA", 175), ("KB-WHO-LBM4", 43),
            ("KB-WHO-LBM4-DESIGN", 55), ("KB-WHO-LBM4-DESIGN", 71),
            ("KB-WHO-LBM4-OUTBREAK", 19), ("KB-WHO-LBM4-OUTBREAK", 38),
            ("KB-WHO-LBM4-PROG", 56),
        })
        self.assertEqual(pending, set())
        self.assertEqual(len(rotated), 67)

    def test_rotated_fallback_pages_are_retained_in_provenance_but_not_candidates(self):
        fallback = {
            ("KB-MY-GMMRA", 42), ("KB-MY-GMMRA", 175), ("KB-WHO-LBM4", 43),
            ("KB-WHO-LBM4-DESIGN", 55), ("KB-WHO-LBM4-DESIGN", 71),
            ("KB-WHO-LBM4-OUTBREAK", 19), ("KB-WHO-LBM4-OUTBREAK", 38),
            ("KB-WHO-LBM4-PROG", 56),
        }
        provenance = {
            (component["document_id"], page["pdf_page_index"])
            for component in self.artifact["components"] for page in component["pages"]
        }
        candidates = {
            (chunk["document_id"], chunk["pdf_page_start"])
            for chunk in self.artifact["candidate_chunks"]
        }
        self.assertTrue(fallback <= provenance)
        self.assertFalse(fallback & candidates)

    def test_all_rotated_warning_pages_are_persistently_selected_for_visual_review(self):
        selection = json.loads(VISUAL_SELECTION.read_text(encoding="utf-8"))
        rows = build_review_ledger(self.report, self.component_map)
        rotated = {
            (row["document_id"], int(row["pdf_page_index"])) for row in rows
            if row["warning"] == "ROTATED_TEXT_OMITTED_BY_LAYOUT_MODE"
        }
        selected = {
            (document_id, page) for document_id, pages in selection.items() for page in pages
        }
        self.assertTrue(rotated <= selected)

    def test_sw404_is_isolated_in_review_gated_waste_code_component(self):
        matches = []
        for component in self.artifact["components"]:
            if component["document_id"] != "KB-MY-SW2005":
                continue
            if "SW 404" in "\n".join(page["text"] for page in component["pages"]):
                matches.append(component["component_id"])
        self.assertEqual(matches, ["KB-MY-SW2005:WASTE_CODE_SCHEDULE"])
        waste_codes = self.by_id["KB-MY-SW2005:WASTE_CODE_SCHEDULE"]
        self.assertIn("VISUAL_VERIFICATION_REQUIRED", waste_codes["review_status"])

    def test_scheduled_waste_domains_are_component_specific(self):
        codes = self.by_id["KB-MY-SW2005:WASTE_CODE_SCHEDULE"]
        labels = self.by_id["KB-MY-SW2005:LABEL_REQUIREMENTS"]
        amendments = self.by_id["KB-MY-SW2005:AMENDMENT_LIST"]
        self.assertEqual(codes["allowed_domains"], ["malaysia_scheduled_waste_codes"])
        self.assertEqual(labels["allowed_domains"], ["malaysia_scheduled_waste_labelling"])
        self.assertEqual(amendments["allowed_domains"], ["malaysia_scheduled_waste_currentness"])

    def test_all_17_sources_are_component_mapped(self):
        extracted_ids = {item["document_id"] for item in self.report["documents"]}
        mapped_ids = {item["document_id"] for item in self.artifact["components"]}
        self.assertEqual(mapped_ids, extracted_ids)
        self.assertEqual(len(mapped_ids), 17)

    def test_who_outer_components_cover_every_page_once(self):
        who_ids = {item["document_id"] for item in self.report["documents"] if "WHO" in item["document_id"]}
        for document_id in who_ids:
            source = next(item for item in self.report["documents"] if item["document_id"] == document_id)
            components = [item for item in self.artifact["components"] if item["document_id"] == document_id]
            pages = [page["pdf_page_index"] for item in components for page in item["pages"]]
            self.assertEqual(pages, list(range(1, source["pdf_page_count"] + 1)), document_id)

    def test_fallback_required_native_pages_are_not_candidates(self):
        prohibited = {
            ("KB-MY-FORME:USER_GUIDE", 26),
            ("KB-MY-FORME:FORM_E_APPLICANT_PART_A", 211),
            *{("KB-MY-SW2005:LABEL_REQUIREMENTS", page) for page in range(18, 24)},
            ("KB-WHO-LBM4-PROG:ANNEXES_BACK_MATTER", 56),
        }
        actual = {
            (chunk["component_id"], chunk["pdf_page_start"])
            for chunk in self.artifact["candidate_chunks"]
        }
        self.assertFalse(prohibited & actual)


if __name__ == "__main__":
    unittest.main()