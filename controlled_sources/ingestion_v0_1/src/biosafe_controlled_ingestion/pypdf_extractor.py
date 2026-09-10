from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from importlib.metadata import version
from pathlib import Path
from typing import Iterable

from pypdf import PdfReader

from .contracts import (
    DocumentExtraction,
    ExtractionReport,
    ExtractionStatus,
    PageRecord,
    SourceRecord,
    SourceStatus,
    ValidationError,
)


DEFAULT_MAX_SOURCE_BYTES = 25 * 1024 * 1024
LOW_TEXT_CHARACTER_THRESHOLD = 100


class _MessageHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


def _normalize_extracted_text(text: str) -> str:
    text = text.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    return re.sub(r"\n{4,}", "\n\n\n", "\n".join(lines)).strip()


def _extract_page_text(page: object) -> tuple[str, tuple[str, ...]]:
    handler = _MessageHandler()
    logger = logging.getLogger("pypdf")
    logger.addHandler(handler)
    try:
        extracted = page.extract_text(extraction_mode="layout") or ""
    finally:
        logger.removeHandler(handler)
    warnings: list[str] = []
    for message in handler.messages:
        normalized = message.casefold()
        if "rotated text" in normalized and "incomplete" in normalized:
            warning = "ROTATED_TEXT_OMITTED_BY_LAYOUT_MODE"
        elif "fonttools is required" in normalized and "cff type1" in normalized:
            warning = "FONT_ENCODING_CFF_REQUIRES_FONTTOOLS"
        elif "symbolsetencoding not implemented" in normalized:
            warning = "FONT_ENCODING_SYMBOLSET_UNSUPPORTED"
        else:
            warning = f"PYPDF_WARNING:{message}"
        if warning not in warnings:
            warnings.append(warning)
    return _normalize_extracted_text(extracted), tuple(warnings)


def _validate_source_bytes(record: SourceRecord, source_path: Path) -> bytes:
    if record.extraction_eligibility != SourceStatus.ELIGIBLE_FOR_OFFLINE_EXTRACTION:
        raise ValidationError(f"{record.document_id} is not eligible for offline extraction")
    raw = source_path.read_bytes()
    if len(raw) != record.size_bytes:
        raise ValidationError(f"{record.document_id} source size changed")
    if hashlib.sha256(raw).hexdigest() != record.source_sha256:
        raise ValidationError(f"{record.document_id} source hash changed")
    if not raw.startswith(b"%PDF-") or b"%%EOF" not in raw[-4096:]:
        raise ValidationError(f"{record.document_id} is not a structurally complete PDF")
    return raw


def extract_document(
    record: SourceRecord,
    staging_dir: Path,
    *,
    max_source_bytes: int = DEFAULT_MAX_SOURCE_BYTES,
) -> DocumentExtraction:
    source_path = staging_dir / record.staged_filename
    parser = f"pypdf=={version('pypdf')}"
    if record.extraction_eligibility != SourceStatus.ELIGIBLE_FOR_OFFLINE_EXTRACTION:
        return DocumentExtraction(
            record.document_id, record.staged_filename, record.source_sha256,
            ExtractionStatus.BLOCKED_SOURCE_VERIFICATION, 0, 0, 0, 0,
            parser, warnings=("SOURCE_NOT_ELIGIBLE_FOR_EXTRACTION",),
        )
    try:
        raw = _validate_source_bytes(record, source_path)
    except (OSError, ValidationError) as exc:
        return DocumentExtraction(
            record.document_id, record.staged_filename, record.source_sha256,
            ExtractionStatus.INVALID_SOURCE, 0, 0, 0, 0,
            parser, warnings=(f"SOURCE_VALIDATION_ERROR:{exc}",),
        )
    if len(raw) > max_source_bytes:
        return DocumentExtraction(
            record.document_id, record.staged_filename, record.source_sha256,
            ExtractionStatus.BLOCKED_SIZE_LIMIT, 0, 0, 0, 0,
            parser, warnings=("SOURCE_EXCEEDS_SIZE_LIMIT",),
        )
    try:
        reader = PdfReader(source_path, strict=False)
    except Exception as exc:  # parser errors vary by PDF structure
        return DocumentExtraction(
            record.document_id, record.staged_filename, record.source_sha256,
            ExtractionStatus.INVALID_SOURCE, 0, 0, 0, 0,
            parser, warnings=(f"PDF_OPEN_ERROR:{type(exc).__name__}:{exc}",),
        )
    document_warnings: list[str] = ["PRINTED_PAGE_LABELS_NOT_VISUALLY_VERIFIED"]
    if reader.is_encrypted:
        try:
            password_type = reader.decrypt("")
        except Exception:
            password_type = 0
        if not password_type:
            return DocumentExtraction(
                record.document_id, record.staged_filename, record.source_sha256,
                ExtractionStatus.BLOCKED_ENCRYPTED, 0, 0, 0, 0,
                parser, warnings=("ENCRYPTED_PDF_REQUIRES_NONEMPTY_PASSWORD",),
            )
        document_warnings.append("PDF_DECRYPTED_WITH_EMPTY_PASSWORD")
    labels = reader.page_labels
    pages: list[PageRecord] = []
    for page_index, page in enumerate(reader.pages, 1):
        warnings: list[str] = []
        try:
            text, parser_warnings = _extract_page_text(page)
            warnings.extend(parser_warnings)
        except Exception as exc:  # retain the page and make the failure auditable
            text = ""
            warnings.append(f"PAGE_EXTRACTION_ERROR:{type(exc).__name__}:{exc}")
        if not text:
            warnings.append("PAGE_TEXT_EMPTY_POSSIBLE_SCAN_OR_DECORATIVE_PAGE")
        elif len(text) < LOW_TEXT_CHARACTER_THRESHOLD:
            warnings.append("PAGE_TEXT_LOW_VOLUME_REVIEW_REQUIRED")
        label = labels[page_index - 1] if page_index - 1 < len(labels) else str(page_index)
        page_record = PageRecord(
            document_id=record.document_id,
            source_sha256=record.source_sha256,
            pdf_page_index=page_index,
            pdf_page_label=str(label),
            printed_page_label="",
            text=text,
            extraction_method=f"pypdf=={version('pypdf')}:layout",
            extraction_warnings=tuple(warnings),
        )
        page_record.validate()
        pages.append(page_record)
        document_warnings.extend(f"PAGE_{page_index}:{warning}" for warning in warnings)
    nonempty = sum(bool(page.text) for page in pages)
    status = ExtractionStatus.EXTRACTED_WITH_WARNINGS if document_warnings else ExtractionStatus.READY
    return DocumentExtraction(
        document_id=record.document_id,
        staged_filename=record.staged_filename,
        source_sha256=record.source_sha256,
        status=status,
        pdf_page_count=len(reader.pages),
        extracted_page_count=len(pages),
        nonempty_page_count=nonempty,
        total_characters=sum(len(page.text) for page in pages),
        parser=parser,
        pages=tuple(pages),
        warnings=tuple(document_warnings),
    )


def extract_documents(
    records: Iterable[SourceRecord],
    staging_dir: Path,
    document_ids: Iterable[str],
) -> ExtractionReport:
    requested = tuple(dict.fromkeys(document_ids))
    by_id = {record.document_id: record for record in records}
    missing = [document_id for document_id in requested if document_id not in by_id]
    if missing:
        raise ValidationError(f"unknown document IDs: {', '.join(missing)}")
    documents = tuple(extract_document(by_id[document_id], staging_dir) for document_id in requested)
    return ExtractionReport(
        report_version="BioSafe_Page_Extraction_v0.1",
        staging_directory=str(staging_dir.resolve()),
        parser=f"pypdf=={version('pypdf')}",
        requested_document_ids=requested,
        documents=documents,
    )


def write_extraction_report(report: ExtractionReport, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, output_path)