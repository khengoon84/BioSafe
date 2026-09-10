from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import os
import shutil
from pathlib import Path
from typing import Any

from .contracts import (
    ExtractionStatus,
    PreflightReport,
    SourceCheck,
    SourceRecord,
    SourceStatus,
    ValidationError,
)


SUPPORTED_MODULE_BACKENDS = ("pypdf", "PyPDF2", "fitz", "pdfplumber")
SUPPORTED_CLI_BACKENDS = ("pdftotext", "mutool")


def detect_extraction_backend() -> str:
    for module in SUPPORTED_MODULE_BACKENDS:
        if importlib.util.find_spec(module) is not None:
            return f"python:{module}"
    for command in SUPPORTED_CLI_BACKENDS:
        path = shutil.which(command)
        if path:
            return f"cli:{path}"
    return "unavailable"


def _tuple_field(value: Any, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ValidationError(f"{field_name} must be a list of non-empty strings")
    return tuple(value)


def load_source_register(register_path: Path, policy_path: Path) -> list[SourceRecord]:
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    policies = policy.get("sources", {})
    with register_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    records: list[SourceRecord] = []
    for row in rows:
        document_id = row["candidate_id"]
        if document_id not in policies:
            raise ValidationError(f"missing source policy for {document_id}")
        item = policies[document_id]
        record = SourceRecord(
            document_id=document_id,
            staged_filename=row["staged_filename"],
            source_sha256=row["sha256"],
            size_bytes=int(row["size_bytes"]),
            title=row["title"] or item["title"],
            publisher=row["publisher"] or item["publisher"],
            jurisdiction=item["jurisdiction"],
            authority_tier=int(item["authority_tier"]),
            document_type=row["expected_document_type"] or item["document_type"],
            publication_date=row["publication_date"] or item["publication_date"],
            currentness_status=row.get("currentness_status", "") or item["currentness_status"],
            supersession_status=row.get("supersession_status", "") or item["supersession_status"],
            official_landing_page=row["official_landing_page"] or item["official_landing_page"],
            direct_download_url=row["direct_download_url"] or item["direct_download_url"],
            allowed_domains=_tuple_field(item["allowed_domains"], "allowed_domains"),
            excluded_domains=_tuple_field(item["excluded_domains"], "excluded_domains"),
            extraction_eligibility=SourceStatus(item["extraction_eligibility"]),
        )
        record.validate()
        records.append(record)
    if len({record.document_id for record in records}) != len(records):
        raise ValidationError("duplicate document_id in source register")
    if len({record.staged_filename for record in records}) != len(records):
        raise ValidationError("duplicate staged_filename in source register")
    return records


def run_preflight(staging_dir: Path, policy_path: Path) -> PreflightReport:
    staging_dir = staging_dir.resolve()
    policy_path = policy_path.resolve()
    register_path = staging_dir / "SOURCE_REGISTER.tsv"
    records = load_source_register(register_path, policy_path)
    backend = detect_extraction_backend()
    seen_hashes: dict[str, str] = {}
    checks: list[SourceCheck] = []
    eligible_count = 0
    for record in records:
        path = staging_dir / record.staged_filename
        warnings: list[str] = []
        if not path.is_file():
            checks.append(SourceCheck(
                record.document_id, record.staged_filename, ExtractionStatus.INVALID_SOURCE,
                record.source_sha256, "", record.size_bytes, 0, False, False, "missing",
                warnings=("SOURCE_FILE_MISSING",),
            ))
            continue
        raw = path.read_bytes()
        observed_hash = hashlib.sha256(raw).hexdigest()
        signature_ok = raw.startswith(b"%PDF-")
        eof_ok = b"%%EOF" in raw[-4096:]
        mode = oct(path.stat().st_mode & 0o777)
        duplicate_of = seen_hashes.get(observed_hash, "")
        seen_hashes.setdefault(observed_hash, record.document_id)
        if duplicate_of:
            warnings.append("DUPLICATE_SOURCE_HASH")
        valid = (
            observed_hash == record.source_sha256
            and len(raw) == record.size_bytes
            and signature_ok
            and eof_ok
            and not duplicate_of
        )
        if not valid:
            status = ExtractionStatus.INVALID_SOURCE
        elif record.extraction_eligibility != SourceStatus.ELIGIBLE_FOR_OFFLINE_EXTRACTION:
            status = ExtractionStatus.BLOCKED_SOURCE_VERIFICATION
            warnings.append("SOURCE_NOT_ELIGIBLE_FOR_EXTRACTION")
        elif backend == "unavailable":
            status = ExtractionStatus.BLOCKED_EXTRACTOR_UNAVAILABLE
            warnings.append("PDF_TEXT_EXTRACTOR_UNAVAILABLE")
            eligible_count += 1
        else:
            status = ExtractionStatus.READY
            eligible_count += 1
        if mode != "0o644":
            warnings.append("UNEXPECTED_FILE_PERMISSIONS")
        checks.append(SourceCheck(
            document_id=record.document_id,
            staged_filename=record.staged_filename,
            status=status,
            registered_sha256=record.source_sha256,
            observed_sha256=observed_hash,
            registered_size_bytes=record.size_bytes,
            observed_size_bytes=len(raw),
            pdf_signature_ok=signature_ok,
            pdf_eof_ok=eof_ok,
            permissions_octal=mode,
            duplicate_of=duplicate_of,
            warnings=tuple(warnings),
        ))
    statuses = {check.status for check in checks}
    if ExtractionStatus.INVALID_SOURCE in statuses:
        overall = ExtractionStatus.INVALID_SOURCE
    elif ExtractionStatus.BLOCKED_SOURCE_VERIFICATION in statuses:
        overall = ExtractionStatus.BLOCKED_SOURCE_VERIFICATION
    elif backend == "unavailable":
        overall = ExtractionStatus.BLOCKED_EXTRACTOR_UNAVAILABLE
    else:
        overall = ExtractionStatus.READY
    report_warnings: list[str] = []
    if ExtractionStatus.INVALID_SOURCE in statuses:
        report_warnings.append(ExtractionStatus.INVALID_SOURCE.value)
    if ExtractionStatus.BLOCKED_SOURCE_VERIFICATION in statuses:
        report_warnings.append(ExtractionStatus.BLOCKED_SOURCE_VERIFICATION.value)
    if backend == "unavailable":
        report_warnings.append(ExtractionStatus.BLOCKED_EXTRACTOR_UNAVAILABLE.value)
    return PreflightReport(
        report_version="BioSafe_Source_Preflight_v0.1",
        staging_directory=str(staging_dir),
        source_register=str(register_path),
        source_policy=str(policy_path),
        extraction_backend=backend,
        overall_status=overall,
        source_count=len(records),
        eligible_source_count=eligible_count,
        checks=tuple(checks),
        warnings=tuple(report_warnings),
    )


def write_report(report: PreflightReport, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, output_path)