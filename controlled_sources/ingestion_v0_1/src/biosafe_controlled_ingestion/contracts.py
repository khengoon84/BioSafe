from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class ValidationError(ValueError):
    """Raised when candidate ingestion data violates a provenance contract."""


class SourceStatus(str, Enum):
    ELIGIBLE_FOR_OFFLINE_EXTRACTION = "ELIGIBLE_FOR_OFFLINE_EXTRACTION"
    HOLD_SOURCE_VERIFICATION = "HOLD_SOURCE_VERIFICATION"


class ExtractionStatus(str, Enum):
    READY = "READY"
    EXTRACTED_WITH_WARNINGS = "EXTRACTED_WITH_WARNINGS"
    BLOCKED_EXTRACTOR_UNAVAILABLE = "BLOCKED_EXTRACTOR_UNAVAILABLE"
    BLOCKED_SOURCE_VERIFICATION = "BLOCKED_SOURCE_VERIFICATION"
    BLOCKED_ENCRYPTED = "BLOCKED_ENCRYPTED"
    BLOCKED_SIZE_LIMIT = "BLOCKED_SIZE_LIMIT"
    INVALID_SOURCE = "INVALID_SOURCE"


def _require_text(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{name} must be a non-empty string")


@dataclass(frozen=True)
class SourceRecord:
    document_id: str
    staged_filename: str
    source_sha256: str
    size_bytes: int
    title: str
    publisher: str
    jurisdiction: str
    authority_tier: int
    document_type: str
    publication_date: str
    currentness_status: str
    supersession_status: str
    official_landing_page: str
    direct_download_url: str
    allowed_domains: tuple[str, ...]
    excluded_domains: tuple[str, ...]
    extraction_eligibility: SourceStatus

    def validate(self) -> None:
        for name in (
            "document_id", "staged_filename", "title", "publisher", "jurisdiction",
            "document_type", "publication_date", "currentness_status",
            "supersession_status", "official_landing_page", "direct_download_url",
        ):
            _require_text(name, getattr(self, name))
        if len(self.source_sha256) != 64 or any(c not in "0123456789abcdef" for c in self.source_sha256):
            raise ValidationError("source_sha256 must be a lowercase SHA-256 digest")
        if self.size_bytes <= 0:
            raise ValidationError("size_bytes must be positive")
        if self.authority_tier not in (1, 2, 3):
            raise ValidationError("authority_tier must be 1, 2, or 3")
        if not self.allowed_domains:
            raise ValidationError("allowed_domains must not be empty")
        if set(self.allowed_domains) & set(self.excluded_domains):
            raise ValidationError("allowed_domains and excluded_domains must not overlap")


@dataclass(frozen=True)
class PageRecord:
    document_id: str
    source_sha256: str
    pdf_page_index: int
    pdf_page_label: str
    printed_page_label: str
    text: str
    extraction_method: str
    extraction_warnings: tuple[str, ...] = ()

    def validate(self) -> None:
        _require_text("document_id", self.document_id)
        _require_text("source_sha256", self.source_sha256)
        _require_text("extraction_method", self.extraction_method)
        if self.pdf_page_index < 1:
            raise ValidationError("pdf_page_index is one-based and must be positive")
        if not isinstance(self.pdf_page_label, str):
            raise ValidationError("pdf_page_label must be a string")
        if not isinstance(self.printed_page_label, str):
            raise ValidationError("printed_page_label must be a string")
        if not isinstance(self.text, str):
            raise ValidationError("text must be a string")


@dataclass(frozen=True)
class DocumentExtraction:
    document_id: str
    staged_filename: str
    source_sha256: str
    status: ExtractionStatus
    pdf_page_count: int
    extracted_page_count: int
    nonempty_page_count: int
    total_characters: int
    parser: str
    pages: tuple[PageRecord, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExtractionReport:
    report_version: str
    staging_directory: str
    parser: str
    requested_document_ids: tuple[str, ...]
    documents: tuple[DocumentExtraction, ...]
    live_activation_status: str = "PROHIBITED_PENDING_PHASE_C_GATES"

    def to_dict(self) -> dict[str, Any]:
        return _as_serializable(self)


@dataclass(frozen=True)
class ChunkRecord:
    chunk_id: str
    document_id: str
    source_sha256: str
    title: str
    publisher: str
    jurisdiction: str
    authority_tier: int
    document_type: str
    publication_date: str
    currentness_status: str
    supersession_status: str
    part: str
    section: str
    subsection: str
    heading: str
    page_start: int
    page_end: int
    printed_page_start: str
    printed_page_end: str
    parent_context: str
    text: str
    scope_domains: tuple[str, ...]
    claim_type: str
    source_url: str
    extraction_method: str
    ingestion_timestamp_utc: str
    extraction_warnings: tuple[str, ...] = ()

    def validate(self) -> None:
        for name in (
            "chunk_id", "document_id", "source_sha256", "title", "publisher",
            "jurisdiction", "document_type", "publication_date", "currentness_status",
            "supersession_status", "text", "claim_type", "source_url",
            "extraction_method", "ingestion_timestamp_utc",
        ):
            _require_text(name, getattr(self, name))
        if self.page_start < 1 or self.page_end < self.page_start:
            raise ValidationError("chunk page range is invalid")
        if not self.scope_domains:
            raise ValidationError("scope_domains must not be empty")
        if self.authority_tier not in (1, 2, 3):
            raise ValidationError("authority_tier must be 1, 2, or 3")


@dataclass(frozen=True)
class SourceCheck:
    document_id: str
    staged_filename: str
    status: ExtractionStatus
    registered_sha256: str
    observed_sha256: str
    registered_size_bytes: int
    observed_size_bytes: int
    pdf_signature_ok: bool
    pdf_eof_ok: bool
    permissions_octal: str
    duplicate_of: str = ""
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class PreflightReport:
    report_version: str
    staging_directory: str
    source_register: str
    source_policy: str
    extraction_backend: str
    overall_status: ExtractionStatus
    source_count: int
    eligible_source_count: int
    checks: tuple[SourceCheck, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return _as_serializable(self)


def _as_serializable(record: Any) -> dict[str, Any]:
    def convert(value: Any) -> Any:
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, tuple):
            return [convert(item) for item in value]
        if isinstance(value, dict):
            return {key: convert(item) for key, item in value.items()}
        return value

    return convert(asdict(record))