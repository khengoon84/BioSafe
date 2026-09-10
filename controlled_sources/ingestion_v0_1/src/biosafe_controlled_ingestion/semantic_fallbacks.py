from __future__ import annotations

import hashlib
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any

from .components import ACTIVATION_PROHIBITED, CLAIM_REVIEW_REQUIRED
from .contracts import ValidationError


FALLBACK_ARTIFACT_VERSION = "BioSafe_Semantic_Fallbacks_v0.1"
FALLBACK_MAP_VERSION = "BioSafe_Semantic_Fallback_Map_v0.1"


def _require_text(name: str, value: Any) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{name} must be a non-empty string")


def _require_sha256(name: str, value: Any) -> None:
    if not isinstance(value, str) or len(value) != 64 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise ValidationError(f"{name} must be a lowercase SHA-256 digest")


def _index_pages(extraction_report: dict[str, Any]) -> dict[tuple[str, int], dict[str, Any]]:
    return {
        (document["document_id"], int(page["pdf_page_index"])): page
        for document in extraction_report["documents"]
        for page in document["pages"]
    }


def _index_renders(render_manifest: dict[str, Any]) -> dict[tuple[str, int], dict[str, Any]]:
    return {
        (item["document_id"], int(item["pdf_page_index"])): item
        for item in render_manifest["renders"]
    }


def _require_unique(items: list[Any], name: str) -> None:
    if len(items) != len(set(items)):
        raise ValidationError(f"{name} must be unique")


def _validate_source_context_blocks(representation: dict[str, Any]) -> None:
    blocks = representation.get("source_context_blocks")
    if blocks is None:
        return
    if not isinstance(blocks, list) or not blocks:
        raise ValidationError("source context blocks must be a non-empty list when present")
    block_ids: list[str] = []
    orders: list[int] = []
    for block in blocks:
        _require_text("source context block ID", block.get("block_id"))
        _require_text("source context block text", block.get("text"))
        order = block.get("source_order")
        if not isinstance(order, int) or order < 1:
            raise ValidationError("source context block order must be a positive integer")
        if "heading" in block and block["heading"] is not None:
            _require_text("source context block heading", block["heading"])
        if "continuation_from_previous_page" in block and not isinstance(
            block["continuation_from_previous_page"], bool
        ):
            raise ValidationError("source context continuation marker must be boolean")
        block_ids.append(block["block_id"])
        orders.append(order)
    _require_unique(block_ids, "source context block IDs")
    if orders != list(range(1, len(blocks) + 1)):
        raise ValidationError("source context block order must be contiguous")


def _validate_table(table: dict[str, Any]) -> None:
    _require_text("table.title", table.get("title"))
    columns = table.get("columns")
    if not isinstance(columns, list) or not columns:
        raise ValidationError("structured table must define columns")
    column_keys: list[str] = []
    for column in columns:
        for field in ("column_key", "stage", "stage_title", "heading"):
            _require_text(f"table column {field}", column.get(field))
        column_keys.append(column["column_key"])
    _require_unique(column_keys, "structured table column keys")

    row_groups = table.get("row_groups")
    if not isinstance(row_groups, list) or not row_groups:
        raise ValidationError("structured table must define row groups")
    labels: list[str] = []
    for row_group in row_groups:
        _require_text("table row-group label", row_group.get("label"))
        labels.append(row_group["label"])
        cells = row_group.get("cells")
        if not isinstance(cells, dict) or set(cells) != set(column_keys):
            raise ValidationError("every row group must contain exactly the declared columns")
        for column_key, lines in cells.items():
            if not isinstance(lines, list) or not lines:
                raise ValidationError(f"table cell {column_key} must contain source-bound lines")
            for line in lines:
                _require_text(f"table cell {column_key} line", line)
    _require_unique(labels, "structured table row-group labels")


def _validate_risk_matrix(matrix: dict[str, Any]) -> None:
    _require_text("risk matrix title", matrix.get("title"))
    _require_text("risk matrix row axis", matrix.get("row_axis"))
    _require_text("risk matrix column axis", matrix.get("column_axis"))
    rows = matrix.get("rows")
    columns = matrix.get("columns")
    if not isinstance(rows, list) or not rows or not isinstance(columns, list) or not columns:
        raise ValidationError("risk matrix must define rows and columns")
    row_keys = []
    column_keys = []
    for item in rows:
        _require_text("risk matrix row key", item.get("key"))
        _require_text("risk matrix row label", item.get("label"))
        row_keys.append(item["key"])
    for item in columns:
        _require_text("risk matrix column key", item.get("key"))
        _require_text("risk matrix column label", item.get("label"))
        column_keys.append(item["key"])
    _require_unique(row_keys, "risk matrix row keys")
    _require_unique(column_keys, "risk matrix column keys")
    cells = matrix.get("cells")
    expected = {f"{row}:{column}" for row in row_keys for column in column_keys}
    if not isinstance(cells, dict) or set(cells) != expected:
        raise ValidationError("risk matrix must contain exactly the complete row-column product")
    allowed = matrix.get("allowed_estimates")
    if not isinstance(allowed, list) or not allowed or any(not isinstance(x, str) for x in allowed):
        raise ValidationError("risk matrix must declare allowed estimates")
    if any(value not in allowed for value in cells.values()):
        raise ValidationError("risk matrix contains an undeclared estimate")
    definitions_status = matrix.get("likelihood_definitions_status", "PRESENT_ON_SOURCE_PAGE")
    if definitions_status not in {"PRESENT_ON_SOURCE_PAGE", "ABSENT_FROM_SOURCE_PAGE"}:
        raise ValidationError("risk matrix likelihood definitions status is invalid")
    definitions = matrix.get("likelihood_definitions")
    if definitions_status == "PRESENT_ON_SOURCE_PAGE":
        if not isinstance(definitions, dict) or set(definitions) != set(row_keys):
            raise ValidationError("risk matrix likelihood definitions must cover every row")
        for value in definitions.values():
            _require_text("risk matrix likelihood definition", value)
    elif definitions is not None:
        raise ValidationError("source-absent likelihood definitions must not be supplied")
    qualifiers = matrix.get("interpretation_qualifiers")
    if not isinstance(qualifiers, list) or not qualifiers:
        raise ValidationError("risk matrix must retain interpretation qualifiers")
    for qualifier in qualifiers:
        _require_text("risk matrix interpretation qualifier", qualifier)
    _validate_source_context_blocks(matrix)


def _validate_directed_flow(flow: dict[str, Any]) -> None:
    _require_text("directed flow title", flow.get("title"))
    nodes = flow.get("nodes")
    edges = flow.get("edges")
    if not isinstance(nodes, list) or not nodes or not isinstance(edges, list) or not edges:
        raise ValidationError("directed flow must define nodes and edges")
    node_ids = []
    node_types = {}
    required_branches: dict[str, Counter[str]] = {}
    allowed_types = {"start", "process", "decision", "terminal", "annotation"}
    for node in nodes:
        _require_text("directed flow node id", node.get("node_id"))
        _require_text("directed flow node label", node.get("label"))
        if node.get("node_type") not in allowed_types:
            raise ValidationError("directed flow node type is invalid")
        node_ids.append(node["node_id"])
        node_types[node["node_id"]] = node["node_type"]
        if node["node_type"] == "decision":
            branches = node.get("required_branch_labels")
            if (
                not isinstance(branches, list)
                or not branches
                or any(not isinstance(branch, str) or not branch.strip() for branch in branches)
            ):
                raise ValidationError("directed flow decision must declare branch labels")
            required_branches[node["node_id"]] = Counter(branches)
    _require_unique(node_ids, "directed flow node IDs")
    if "start" not in node_types.values() or "terminal" not in node_types.values():
        raise ValidationError("directed flow must contain start and terminal nodes")
    edge_ids = []
    incoming: dict[str, int] = {node_id: 0 for node_id in node_ids}
    outgoing: dict[str, int] = {node_id: 0 for node_id in node_ids}
    observed_branches: dict[str, Counter[str]] = {
        key: Counter() for key in required_branches
    }
    for edge in edges:
        _require_text("directed flow edge id", edge.get("edge_id"))
        _require_text("directed flow edge source", edge.get("source"))
        _require_text("directed flow edge target", edge.get("target"))
        if edge["source"] not in node_types or edge["target"] not in node_types:
            raise ValidationError("directed flow edge references an unknown node")
        edge_ids.append(edge["edge_id"])
        outgoing[edge["source"]] += 1
        incoming[edge["target"]] += 1
        label = edge.get("label", "")
        if not isinstance(label, str):
            raise ValidationError("directed flow edge label must be a string")
        if edge["source"] in observed_branches and label:
            observed_branches[edge["source"]][label] += 1
    _require_unique(edge_ids, "directed flow edge IDs")
    if any(incoming[node_id] == 0 for node_id, node_type in node_types.items() if node_type != "start"):
        raise ValidationError("directed flow contains a disconnected non-start node")
    if any(outgoing[node_id] == 0 for node_id, node_type in node_types.items() if node_type != "terminal"):
        raise ValidationError("directed flow contains a disconnected non-terminal node")
    for node_id, required in required_branches.items():
        if observed_branches[node_id] != required:
            raise ValidationError("directed flow decision branches do not match declared labels")
    _validate_source_context_blocks(flow)


def _validate_illustrated_sequence(sequence: dict[str, Any]) -> None:
    _require_text("illustrated sequence caption", sequence.get("caption"))
    if sequence.get("observation_only") is not True:
        raise ValidationError("illustrated sequence must be observation-only")
    if sequence.get("source_has_textual_step_labels") is not False:
        raise ValidationError("unlabelled illustrated sequence must record absent textual step labels")
    frames = sequence.get("frames")
    if not isinstance(frames, list) or not frames:
        raise ValidationError("illustrated sequence must define frames")
    if [frame.get("frame_number") for frame in frames] != list(range(1, len(frames) + 1)):
        raise ValidationError("illustrated sequence frame numbers must be contiguous")
    forbidden = {"instruction", "required_action", "safety_outcome"}
    for frame in frames:
        if forbidden & set(frame):
            raise ValidationError("observation-only frame contains inferred procedural fields")
        _require_text("illustrated sequence observation", frame.get("visible_observation"))


def _validate_graphical_label_set(label_set: dict[str, Any]) -> None:
    for field in ("schedule", "regulation_reference", "title"):
        _require_text(f"graphical label set {field}", label_set.get(field))
    labels = label_set.get("labels")
    if not isinstance(labels, list) or not labels:
        raise ValidationError("graphical label set must define labels")
    ids = []
    printed_numbers = []
    for label in labels:
        for field in ("label_id", "hazard_name", "waste_qualifier", "symbol_description", "symbol_color", "background_color"):
            _require_text(f"graphical label {field}", label.get(field))
        ids.append(label["label_id"])
        printed = label.get("printed_label_number")
        if printed is not None:
            if not isinstance(printed, int) or printed < 1:
                raise ValidationError("printed label number must be a positive integer or null")
            printed_numbers.append(printed)
    _require_unique(ids, "graphical label IDs")
    _require_unique(printed_numbers, "printed label numbers")

    enhanced = label_set.get("source_page_sequence")
    if enhanced is not None:
        if not isinstance(enhanced, int) or enhanced < 1:
            raise ValidationError("graphical label source page sequence must be positive")
        allowed_alignment = {"MATCH", "CONFLICT", "UNRESOLVED"}
        for label in labels:
            _require_text("graphical label rendered glyph observation", label.get("rendered_glyph_observation"))
            alignment = label.get("glyph_text_alignment")
            if alignment not in allowed_alignment:
                raise ValidationError("graphical label glyph/text alignment is invalid")
            explanation = label.get("glyph_text_alignment_explanation")
            if alignment == "MATCH":
                if explanation is not None:
                    _require_text("graphical label alignment explanation", explanation)
            else:
                _require_text("graphical label conflict explanation", explanation)

        continuations = label_set.get("cross_page_number_assignments", [])
        if not isinstance(continuations, list):
            raise ValidationError("cross-page number assignments must be a list")
        continuation_numbers: list[int] = []
        for continuation in continuations:
            for field in ("target_label_id", "visible_marker"):
                _require_text(f"cross-page number assignment {field}", continuation.get(field))
            previous_page = continuation.get("target_pdf_page_index")
            printed = continuation.get("printed_label_number")
            if not isinstance(previous_page, int) or previous_page < 1:
                raise ValidationError("cross-page target page must be positive")
            if not isinstance(printed, int) or printed < 1:
                raise ValidationError("cross-page printed label number must be positive")
            continuation_numbers.append(printed)
        _require_unique(continuation_numbers, "cross-page printed label numbers")

        requirements = label_set.get("label_requirements")
        if requirements is not None:
            _require_text("label requirements heading", requirements.get("heading"))
            numbered = requirements.get("numbered_requirements")
            if not isinstance(numbered, list) or not numbered:
                raise ValidationError("label requirements must contain numbered requirements")
            if [item.get("number") for item in numbered] != list(range(1, len(numbered) + 1)):
                raise ValidationError("label requirement numbers must be contiguous")
            for item in numbered:
                _require_text("label requirement text", item.get("text"))
            color_rows = requirements.get("color_reference_rows")
            if not isinstance(color_rows, list) or not color_rows:
                raise ValidationError("label requirements must contain color reference rows")
            colors: list[str] = []
            for row in color_rows:
                _require_text("label requirement color", row.get("color"))
                _require_text("label requirement reference", row.get("reference_number"))
                colors.append(row["color"])
            _require_unique(colors, "label requirement colors")


def _validate_cross_page_label_assignments(units: list[dict[str, Any]]) -> None:
    labels_by_page: dict[tuple[str, int], dict[str, dict[str, Any]]] = {}
    assignments: list[tuple[dict[str, Any], dict[str, Any]]] = []
    printed_by_document: dict[str, list[int]] = {}
    for unit in units:
        representation = unit.get("structured_representation", {})
        if representation.get("representation_type") != "graphical_label_set":
            continue
        key = (unit["document_id"], unit["pdf_page_index"])
        labels_by_page[key] = {label["label_id"]: label for label in representation["labels"]}
        assignments.extend((unit, item) for item in representation.get("cross_page_number_assignments", []))
        printed_by_document.setdefault(unit["document_id"], []).extend(
            label["printed_label_number"]
            for label in representation["labels"]
            if label.get("printed_label_number") is not None
        )
    for unit, assignment in assignments:
        target_page = assignment["target_pdf_page_index"]
        if target_page != unit["pdf_page_index"] - 1:
            raise ValidationError("cross-page number assignment must target the immediately preceding page")
        target = labels_by_page.get((unit["document_id"], target_page), {}).get(
            assignment["target_label_id"]
        )
        if target is None:
            raise ValidationError("cross-page number assignment target label does not exist")
        if target.get("printed_label_number") is not None:
            raise ValidationError("cross-page number assignment target already has a printed number")
        if assignment["visible_marker"] != f"Label {assignment['printed_label_number']}":
            raise ValidationError("cross-page visible marker does not match assigned number")
        printed_by_document.setdefault(unit["document_id"], []).append(
            assignment["printed_label_number"]
        )
    for document_id, printed in printed_by_document.items():
        _require_unique(printed, f"graphical label printed numbers for {document_id}")


def _validate_representation(representation: dict[str, Any]) -> None:
    representation_type = representation.get("representation_type")
    validators = {
        "structured_table": _validate_table,
        "risk_matrix": _validate_risk_matrix,
        "directed_flow": _validate_directed_flow,
        "illustrated_sequence": _validate_illustrated_sequence,
        "graphical_label_set": _validate_graphical_label_set,
    }
    validator = validators.get(representation_type)
    if validator is None:
        raise ValidationError(f"unsupported fallback representation type: {representation_type}")
    validator(representation)


def build_semantic_fallback_artifact(
    fallback_map: dict[str, Any],
    extraction_report: dict[str, Any],
    render_manifest: dict[str, Any],
    component_artifact: dict[str, Any],
) -> dict[str, Any]:
    if fallback_map.get("fallback_map_version") != FALLBACK_MAP_VERSION:
        raise ValidationError("unsupported semantic fallback map version")
    if fallback_map.get("live_activation_status") != ACTIVATION_PROHIBITED:
        raise ValidationError("semantic fallback map must prohibit live activation")
    if fallback_map.get("claim_use_status") != CLAIM_REVIEW_REQUIRED:
        raise ValidationError("semantic fallback map must require claim review")

    pages = _index_pages(extraction_report)
    renders = _index_renders(render_manifest)
    component_pages = {
        (component["component_id"], page["pdf_page_index"])
        for component in component_artifact.get("components", [])
        for page in component["pages"]
    }
    native_candidates = {
        (chunk["document_id"], chunk["pdf_page_start"])
        for chunk in component_artifact.get("candidate_chunks", [])
    }
    units: list[dict[str, Any]] = []
    unit_ids: set[str] = set()
    page_keys: set[tuple[str, int]] = set()
    for raw in fallback_map.get("fallback_units", []):
        unit_id = raw.get("fallback_unit_id")
        _require_text("fallback_unit_id", unit_id)
        if unit_id in unit_ids:
            raise ValidationError(f"duplicate fallback_unit_id: {unit_id}")
        unit_ids.add(unit_id)
        document_id = raw.get("document_id")
        _require_text("document_id", document_id)
        page_index = raw.get("pdf_page_index")
        if not isinstance(page_index, int) or page_index < 1:
            raise ValidationError("pdf_page_index must be a positive integer")
        page_key = (document_id, page_index)
        if page_key in page_keys:
            raise ValidationError("only one semantic fallback unit is allowed per source page")
        page_keys.add(page_key)

        source_sha256 = raw.get("source_sha256")
        render_sha256 = raw.get("render_sha256")
        _require_sha256("source_sha256", source_sha256)
        _require_sha256("render_sha256", render_sha256)
        source_page = pages.get(page_key)
        render = renders.get(page_key)
        if source_page is None:
            raise ValidationError(f"fallback source page not found: {document_id} page {page_index}")
        if render is None:
            raise ValidationError(f"fallback render not found: {document_id} page {page_index}")
        if source_page["source_sha256"] != source_sha256 or render["source_sha256"] != source_sha256:
            raise ValidationError("fallback source hash does not match page and render provenance")
        if render["rendered_sha256"] != render_sha256:
            raise ValidationError("fallback render hash does not match render manifest")
        if raw.get("rendered_filename") != render["rendered_filename"]:
            raise ValidationError("fallback rendered filename does not match render manifest")
        if raw.get("pdf_page_label") != source_page["pdf_page_label"]:
            raise ValidationError("fallback PDF page label does not match immutable page record")
        if raw.get("native_extraction_warning") not in source_page["extraction_warnings"]:
            raise ValidationError("fallback warning is absent from immutable page record")
        if raw.get("native_candidate_status") != "EXCLUDED_PENDING_REVIEWED_FALLBACK_INTEGRATION":
            raise ValidationError("native fallback page must remain explicitly excluded")
        for field in (
            "component_id", "fallback_type", "review_basis", "transcription_status",
            "semantic_review_status", "human_review_status",
        ):
            _require_text(field, raw.get(field))
        if (raw["component_id"], page_index) not in component_pages:
            raise ValidationError("fallback page is absent from named component provenance")
        if page_key in native_candidates:
            raise ValidationError("fallback native page is still present in component candidates")
        if raw["transcription_status"] != "SOURCE_BOUND_TRANSCRIPTION_COMPLETE":
            raise ValidationError("fallback transcription must be source-bound and complete")
        if raw["semantic_review_status"] != "SOURCE_BOUND_SEMANTIC_COMPARISON_COMPLETE":
            raise ValidationError("fallback semantic comparison must be source-bound and complete")
        if raw["human_review_status"] != "HUMAN_REVIEW_REQUIRED":
            raise ValidationError("fallback human review must remain explicitly required")
        limitations = raw.get("limitations")
        if not isinstance(limitations, list) or not limitations:
            raise ValidationError("fallback unit must record limitations")
        for limitation in limitations:
            _require_text("fallback limitation", limitation)
        _validate_representation(raw.get("structured_representation", {}))

        unit = dict(raw)
        unit["native_extraction_method"] = source_page["extraction_method"]
        unit["native_text_sha256"] = hashlib.sha256(
            source_page["text"].encode("utf-8")
        ).hexdigest()
        unit["claim_use_status"] = CLAIM_REVIEW_REQUIRED
        unit["live_activation_status"] = ACTIVATION_PROHIBITED
        units.append(unit)

    if not units:
        raise ValidationError("semantic fallback map must contain at least one unit")
    _validate_cross_page_label_assignments(units)
    return {
        "artifact_version": FALLBACK_ARTIFACT_VERSION,
        "source_extraction_report_version": extraction_report.get("report_version", ""),
        "render_manifest_version": render_manifest.get("manifest_version", ""),
        "source_component_artifact_version": component_artifact.get("artifact_version", ""),
        "claim_use_status": CLAIM_REVIEW_REQUIRED,
        "live_activation_status": ACTIVATION_PROHIBITED,
        "fallback_units": sorted(units, key=lambda item: item["fallback_unit_id"]),
    }


def write_semantic_fallback_artifact(artifact: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, output)