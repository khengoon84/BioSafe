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
from biosafe_controlled_ingestion.semantic_fallbacks import (  # noqa: E402
    build_semantic_fallback_artifact,
    write_semantic_fallback_artifact,
)


FALLBACK_MAP = INGESTION / "config/semantic_fallback_map_v0_1.json"
PAGES = INGESTION / "reports/all_sources_pages_v0_1.json"
RENDERS = INGESTION / "reports/targeted_visual_review_v0_1/RENDER_MANIFEST.json"
COMPONENTS = INGESTION / "reports/component_candidates_v0_1.json"


class SemanticFallbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fallback_map = json.loads(FALLBACK_MAP.read_text(encoding="utf-8"))
        cls.pages = json.loads(PAGES.read_text(encoding="utf-8"))
        cls.renders = json.loads(RENDERS.read_text(encoding="utf-8"))
        cls.components = json.loads(COMPONENTS.read_text(encoding="utf-8"))
        cls.artifact = build_semantic_fallback_artifact(
            cls.fallback_map, cls.pages, cls.renders, cls.components
        )
        cls.by_id = {
            unit["fallback_unit_id"]: unit for unit in cls.artifact["fallback_units"]
        }

    @staticmethod
    def _unit_id(fragment: str) -> str:
        return next(
            unit_id for unit_id in SemanticFallbackTests.by_id if fragment in unit_id
        )

    @classmethod
    def _page_unit(cls, document_id: str, page: int) -> dict:
        return next(
            unit for unit in cls.artifact["fallback_units"]
            if unit["document_id"] == document_id and unit["pdf_page_index"] == page
        )

    def test_all_twelve_units_are_hash_bound_and_activation_prohibited(self):
        self.assertEqual(len(self.artifact["fallback_units"]), 12)
        unit = self.by_id[self._unit_id("KB-WHO-LBM4-PROG:")]
        self.assertEqual(
            unit["source_sha256"],
            "4c76c350e0835b8274ac3651fc40de65e6b2481be302c7b3c0d012aac248ef65",
        )
        self.assertEqual(
            unit["render_sha256"],
            "3b92b204753b3dd702449b21808126f9c15879ec5329fba386921726033ea7d4",
        )
        self.assertEqual(self.artifact["claim_use_status"], CLAIM_REVIEW_REQUIRED)
        self.assertEqual(self.artifact["live_activation_status"], ACTIVATION_PROHIBITED)
        for unit in self.artifact["fallback_units"]:
            self.assertEqual(
                hashlib.sha256(
                    (INGESTION / "reports/targeted_visual_review_v0_1" / unit["rendered_filename"]).read_bytes()
                ).hexdigest(),
                unit["render_sha256"],
            )
            self.assertEqual(unit["human_review_status"], "HUMAN_REVIEW_REQUIRED")
            self.assertEqual(unit["claim_use_status"], CLAIM_REVIEW_REQUIRED)
            self.assertEqual(unit["live_activation_status"], ACTIVATION_PROHIBITED)

    def test_prog_table_preserves_exact_stage_column_and_row_group_structure(self):
        table = self.by_id[self._unit_id("KB-WHO-LBM4-PROG:")]["structured_representation"]
        self.assertEqual(
            [(column["stage"], column["heading"]) for column in table["columns"]],
            [
                ("Step 1", "Asset inventory"),
                ("Step 2", "Risk scenarios"),
                ("Step 2", "Likelihood"),
                ("Step 2", "Consequences"),
                ("Step 3", "Risk control measures"),
                ("Step 3", "Vulnerability assessment"),
                ("Step 4", "Strategy review"),
            ],
        )
        self.assertEqual([group["label"] for group in table["row_groups"]], ["Description", "Examples"])
        expected_keys = {column["column_key"] for column in table["columns"]}
        for group in table["row_groups"]:
            self.assertEqual(set(group["cells"]), expected_keys)
        examples = table["row_groups"][1]["cells"]
        self.assertIn("extortion", examples["risk_scenarios"])
        self.assertIn("Emergency response: incident reporting", examples["risk_control_measures"])
        self.assertEqual(examples["strategy_review"], ["acceptable", "not acceptable"])

    def test_gmmra_matrix_and_qualifiers_are_exact(self):
        matrix = self._page_unit("KB-MY-GMMRA", 42)["structured_representation"]
        self.assertEqual(len(matrix["cells"]), 16)
        self.assertEqual(matrix["cells"]["highly_unlikely:major"], "Moderate")
        self.assertEqual(matrix["cells"]["highly_likely:marginal"], "Low")
        self.assertEqual(matrix["cells"]["likely:major"], "High")
        self.assertEqual(
            matrix["likelihood_definitions"]["highly_likely"],
            "Is expected to occur in most circumstances",
        )
        qualifiers = " ".join(matrix["interpretation_qualifiers"]).lower()
        self.assertIn("should not be seen as definitive", qualifiers)
        self.assertIn("uncertainty", qualifiers)
        self.assertIn("assumptions", qualifiers)

    def test_design_flow_preserves_decisions_loops_bypass_and_stop(self):
        flow = self._page_unit("KB-WHO-LBM4-DESIGN", 55)["structured_representation"]
        edges = {(edge["source"], edge["target"], edge["label"]) for edge in flow["edges"]}
        self.assertIn(("approve_concept", "revise_concept", "No"), edges)
        self.assertIn(("revise_concept", "concept_design", ""), edges)
        self.assertIn(("approve_schematic", "detailed_design", "Yes"), edges)
        self.assertIn(("approve_detailed", "unacceptable", "No"), edges)
        self.assertIn(("approve_detailed", "revise_detailed", "No"), edges)
        self.assertIn(("unacceptable", "stop", ""), edges)
        self.assertIn(("choose_procurement", "procurement_note", "route-dependent bypass"), edges)
        revision = next(edge for edge in flow["edges"] if edge["edge_id"] == "e16")
        self.assertEqual(revision["label"], "No")
        detailed = next(node for node in flow["nodes"] if node["node_id"] == "approve_detailed")
        self.assertEqual(detailed["required_branch_labels"], ["Yes", "No", "No"])

    def test_ppe_sequence_is_ordered_observation_only(self):
        sequence = self.by_id[self._unit_id("KB-WHO-LBM4-PPE:")]["structured_representation"]
        self.assertEqual(sequence["caption"], "Figure 6.2 Procedure to remove a disposable apron")
        self.assertTrue(sequence["observation_only"])
        self.assertFalse(sequence["source_has_textual_step_labels"])
        self.assertEqual([frame["frame_number"] for frame in sequence["frames"]], [1, 2, 3, 4, 5])
        for frame in sequence["frames"]:
            self.assertFalse({"instruction", "required_action", "safety_outcome"} & set(frame))

    def test_scheduled_waste_page_18_has_no_invented_second_label_number(self):
        label_set = self._page_unit("KB-MY-SW2005", 18)["structured_representation"]
        self.assertEqual(label_set["schedule"], "JADUAL KETIGA")
        self.assertEqual(label_set["regulation_reference"], "Peraturan 10")
        self.assertEqual(label_set["labels"][0]["printed_label_number"], 1)
        self.assertIsNone(label_set["labels"][1]["printed_label_number"])
        self.assertEqual(label_set["labels"][0]["symbol_description"], "bom meletup")
        self.assertEqual(label_set["labels"][1]["background_color"], "merah")

    def test_gmmra_page_175_preserves_matrix_context_without_borrowed_key(self):
        matrix = self._page_unit("KB-MY-GMMRA", 175)["structured_representation"]
        self.assertEqual(matrix["title"], "Table 15: Risk estimation matrix")
        self.assertEqual(len(matrix["cells"]), 16)
        self.assertEqual(matrix["cells"]["highly_likely:marginal"], "Low")
        self.assertEqual(matrix["cells"]["highly_unlikely:major"], "Moderate")
        self.assertEqual(matrix["likelihood_definitions_status"], "ABSENT_FROM_SOURCE_PAGE")
        self.assertNotIn("likelihood_definitions", matrix)
        self.assertTrue(matrix["source_context_blocks"][0]["continuation_from_previous_page"])
        self.assertIn("balanced view", matrix["source_context_blocks"][-1]["text"])

    def test_operational_flow_preserves_three_paths_convergence_and_context(self):
        flow = self._page_unit("KB-WHO-LBM4-DESIGN", 71)["structured_representation"]
        edges = {(edge["source"], edge["target"]) for edge in flow["edges"]}
        self.assertEqual(
            {target for source, target in edges if source == "consider"},
            {"in_house", "managed", "contractors"},
        )
        self.assertTrue({("in_house", "plan"), ("managed", "plan"), ("contractors", "plan")} <= edges)
        self.assertIn(("assess", "improve"), edges)
        self.assertFalse(any(node["node_type"] == "decision" for node in flow["nodes"]))
        self.assertIn("two types of maintenance", flow["source_context_blocks"][0]["text"])

    def test_scheduled_waste_pages_preserve_numbering_conflicts_and_requirements(self):
        page19 = self._page_unit("KB-MY-SW2005", 19)["structured_representation"]
        self.assertEqual(page19["cross_page_number_assignments"], [{
            "target_label_id": "page18_flammable_liquid_waste",
            "target_pdf_page_index": 18,
            "printed_label_number": 2,
            "visible_marker": "Label 2",
        }])
        observed = []
        for page in range(19, 24):
            observed.extend(
                label["printed_label_number"]
                for label in self._page_unit("KB-MY-SW2005", page)["structured_representation"]["labels"]
            )
        self.assertEqual(observed, list(range(3, 12)))
        infectious = self._page_unit("KB-MY-SW2005", 22)["structured_representation"]["labels"][0]
        self.assertEqual(infectious["glyph_text_alignment"], "CONFLICT")
        self.assertIn("three-crescent", infectious["glyph_text_alignment_explanation"])
        page23 = self._page_unit("KB-MY-SW2005", 23)["structured_representation"]
        self.assertEqual(page23["labels"][0]["glyph_text_alignment"], "CONFLICT")
        requirements = page23["label_requirements"]
        self.assertEqual([x["number"] for x in requirements["numbered_requirements"]], [1, 2, 3])
        self.assertEqual(
            [(x["color"], x["reference_number"]) for x in requirements["color_reference_rows"]],
            [("Biru tua", "166"), ("Kuning burung kenari", "309"),
             ("Merah isyarat", "537"), ("Jingga lembut", "557")],
        )

    def test_all_fallback_pages_remain_provenance_only_and_not_candidates(self):
        provenance = {
            (component["document_id"], page["pdf_page_index"])
            for component in self.components["components"]
            for page in component["pages"]
        }
        candidates = {
            (chunk["document_id"], chunk["pdf_page_start"])
            for chunk in self.components["candidate_chunks"]
        }
        fallback_pages = {
            (unit["document_id"], unit["pdf_page_index"])
            for unit in self.artifact["fallback_units"]
        }
        self.assertEqual(fallback_pages, {
            ("KB-WHO-LBM4-PROG", 56),
            ("KB-MY-GMMRA", 42),
            ("KB-WHO-LBM4-DESIGN", 55),
            ("KB-WHO-LBM4-PPE", 42),
            ("KB-MY-SW2005", 18),
            ("KB-MY-SW2005", 19),
            ("KB-MY-SW2005", 20),
            ("KB-MY-SW2005", 21),
            ("KB-MY-SW2005", 22),
            ("KB-MY-SW2005", 23),
            ("KB-MY-GMMRA", 175),
            ("KB-WHO-LBM4-DESIGN", 71),
        })
        self.assertTrue(fallback_pages <= provenance)
        self.assertFalse(fallback_pages & candidates)
        self.assertNotIn("fallback_units", self.components)

    def test_common_contract_tampering_fails_closed(self):
        bad_hash = json.loads(json.dumps(self.fallback_map))
        bad_hash["fallback_units"][0]["render_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValidationError, "render hash"):
            build_semantic_fallback_artifact(bad_hash, self.pages, self.renders, self.components)

        human_passed = json.loads(json.dumps(self.fallback_map))
        human_passed["fallback_units"][0]["human_review_status"] = "PASSED"
        with self.assertRaisesRegex(ValidationError, "human review"):
            build_semantic_fallback_artifact(human_passed, self.pages, self.renders, self.components)

        unknown_type = json.loads(json.dumps(self.fallback_map))
        unknown_type["fallback_units"][0]["structured_representation"]["representation_type"] = "unknown"
        with self.assertRaisesRegex(ValidationError, "unsupported"):
            build_semantic_fallback_artifact(unknown_type, self.pages, self.renders, self.components)

        candidate_present = json.loads(json.dumps(self.components))
        candidate_present["candidate_chunks"].append({
            "document_id": "KB-WHO-LBM4-PROG", "pdf_page_start": 56,
        })
        with self.assertRaisesRegex(ValidationError, "still present"):
            build_semantic_fallback_artifact(
                self.fallback_map, self.pages, self.renders, candidate_present
            )

    def test_representation_specific_tampering_fails_closed(self):
        cases = []
        missing_table_cell = json.loads(json.dumps(self.fallback_map))
        prog = next(x for x in missing_table_cell["fallback_units"] if x["document_id"] == "KB-WHO-LBM4-PROG")
        del prog["structured_representation"]["row_groups"][0]["cells"]["likelihood"]
        cases.append((missing_table_cell, "exactly the declared columns"))

        missing_matrix_cell = json.loads(json.dumps(self.fallback_map))
        matrix = next(x for x in missing_matrix_cell["fallback_units"] if x["document_id"] == "KB-MY-GMMRA" and x["pdf_page_index"] == 42)
        del matrix["structured_representation"]["cells"]["likely:major"]
        cases.append((missing_matrix_cell, "complete row-column product"))

        dangling_flow = json.loads(json.dumps(self.fallback_map))
        flow = next(x for x in dangling_flow["fallback_units"] if x["document_id"] == "KB-WHO-LBM4-DESIGN" and x["pdf_page_index"] == 55)
        flow["structured_representation"]["edges"][0]["target"] = "missing"
        cases.append((dangling_flow, "unknown node"))

        missing_duplicate_branch = json.loads(json.dumps(self.fallback_map))
        flow = next(
            x for x in missing_duplicate_branch["fallback_units"]
            if x["document_id"] == "KB-WHO-LBM4-DESIGN" and x["pdf_page_index"] == 55
        )
        revision = next(
            edge for edge in flow["structured_representation"]["edges"]
            if edge["edge_id"] == "e16"
        )
        revision["label"] = ""
        cases.append((missing_duplicate_branch, "decision branches do not match"))

        disconnected_flow = json.loads(json.dumps(self.fallback_map))
        flow = next(x for x in disconnected_flow["fallback_units"] if x["document_id"] == "KB-WHO-LBM4-DESIGN" and x["pdf_page_index"] == 55)
        flow["structured_representation"]["nodes"].append({
            "node_id": "orphan", "node_type": "process", "label": "Orphan",
        })
        cases.append((disconnected_flow, "disconnected non-start node"))

        inferred_instruction = json.loads(json.dumps(self.fallback_map))
        sequence = next(x for x in inferred_instruction["fallback_units"] if x["document_id"] == "KB-WHO-LBM4-PPE")
        sequence["structured_representation"]["frames"][0]["instruction"] = "Do something"
        cases.append((inferred_instruction, "inferred procedural fields"))

        incomplete_label = json.loads(json.dumps(self.fallback_map))
        labels = next(x for x in incomplete_label["fallback_units"] if x["document_id"] == "KB-MY-SW2005" and x["pdf_page_index"] == 18)
        del labels["structured_representation"]["labels"][0]["symbol_color"]
        cases.append((incomplete_label, "symbol_color"))

        partial_absent_key = json.loads(json.dumps(self.fallback_map))
        matrix = next(x for x in partial_absent_key["fallback_units"] if x["document_id"] == "KB-MY-GMMRA" and x["pdf_page_index"] == 175)
        matrix["structured_representation"]["likelihood_definitions"] = {"likely": "borrowed"}
        cases.append((partial_absent_key, "source-absent likelihood definitions"))

        missing_context = json.loads(json.dumps(self.fallback_map))
        flow = next(x for x in missing_context["fallback_units"] if x["document_id"] == "KB-WHO-LBM4-DESIGN" and x["pdf_page_index"] == 71)
        flow["structured_representation"]["source_context_blocks"][0]["text"] = ""
        cases.append((missing_context, "source context block text"))

        bad_continuation = json.loads(json.dumps(self.fallback_map))
        labels = next(x for x in bad_continuation["fallback_units"] if x["document_id"] == "KB-MY-SW2005" and x["pdf_page_index"] == 19)
        labels["structured_representation"]["cross_page_number_assignments"][0]["target_pdf_page_index"] = 17
        cases.append((bad_continuation, "immediately preceding page"))

        wrong_visible_number = json.loads(json.dumps(self.fallback_map))
        labels = next(x for x in wrong_visible_number["fallback_units"] if x["document_id"] == "KB-MY-SW2005" and x["pdf_page_index"] == 19)
        labels["structured_representation"]["cross_page_number_assignments"][0]["printed_label_number"] = 3
        cases.append((wrong_visible_number, "visible marker does not match"))

        unexplained_conflict = json.loads(json.dumps(self.fallback_map))
        labels = next(x for x in unexplained_conflict["fallback_units"] if x["document_id"] == "KB-MY-SW2005" and x["pdf_page_index"] == 22)
        labels["structured_representation"]["labels"][0]["glyph_text_alignment_explanation"] = ""
        cases.append((unexplained_conflict, "conflict explanation"))

        missing_requirements = json.loads(json.dumps(self.fallback_map))
        labels = next(x for x in missing_requirements["fallback_units"] if x["document_id"] == "KB-MY-SW2005" and x["pdf_page_index"] == 23)
        labels["structured_representation"]["label_requirements"]["numbered_requirements"] = []
        cases.append((missing_requirements, "numbered requirements"))

        for changed, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(ValidationError, message):
                build_semantic_fallback_artifact(changed, self.pages, self.renders, self.components)

    def test_serialization_is_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "fallbacks.json"
            write_semantic_fallback_artifact(self.artifact, output)
            first = output.read_bytes()
            write_semantic_fallback_artifact(self.artifact, output)
            self.assertEqual(first, output.read_bytes())


if __name__ == "__main__":
    unittest.main()