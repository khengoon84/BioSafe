#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import struct
import zlib
from pathlib import Path

import numpy as np
import pypdfium2 as pdfium


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    body = kind + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


def write_rgb_png(array: np.ndarray, output: Path) -> None:
    if array.ndim != 3 or array.shape[2] not in (3, 4):
        raise ValueError("expected an RGB or RGBA image")
    rgb = np.ascontiguousarray(array[:, :, :3], dtype=np.uint8)
    height, width, _ = rgb.shape
    scanlines = b"".join(b"\x00" + rgb[row].tobytes() for row in range(height))
    payload = (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + _png_chunk(b"IDAT", zlib.compress(scanlines, level=9))
        + _png_chunk(b"IEND", b"")
    )
    output.write_bytes(payload)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render local PDF pages for extraction review.")
    parser.add_argument("--staging-dir", required=True, type=Path)
    parser.add_argument("--register", required=True, type=Path)
    parser.add_argument("--selection", required=True, type=Path,
                        help="JSON object mapping document IDs to one-based page lists")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--scale", type=float, default=1.5)
    args = parser.parse_args()
    if args.scale <= 0 or args.scale > 4:
        raise ValueError("scale must be greater than zero and no more than four")
    selected = json.loads(args.selection.read_text(encoding="utf-8"))
    registered = {
        row["candidate_id"]: row
        for row in csv.DictReader(args.register.open(encoding="utf-8"), delimiter="\t")
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    for document_id, page_indexes in selected.items():
        if document_id not in registered:
            raise ValueError(f"unregistered document: {document_id}")
        record = registered[document_id]
        source = args.staging_dir / record["staged_filename"]
        observed = hashlib.sha256(source.read_bytes()).hexdigest()
        if observed != record["sha256"]:
            raise ValueError(f"source hash changed: {document_id}")
        pdf = pdfium.PdfDocument(source)
        for one_based_index in page_indexes:
            if one_based_index < 1 or one_based_index > len(pdf):
                raise ValueError(f"invalid page {one_based_index} for {document_id}")
            bitmap = pdf[one_based_index - 1].render(scale=args.scale)
            image = bitmap.to_numpy()
            output = args.output_dir / f"{document_id}_page_{one_based_index:03d}.png"
            write_rgb_png(image, output)
            manifest.append({
                "document_id": document_id,
                "source_sha256": observed,
                "pdf_page_index": one_based_index,
                "render_scale": args.scale,
                "rendered_filename": output.name,
                "rendered_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            })
    (args.output_dir / "RENDER_MANIFEST.json").write_text(
        json.dumps({
            "renderer": "pypdfium2==5.13.0",
            "purpose": "LOCAL_EXTRACTION_REVIEW_ONLY",
            "renders": manifest,
        }, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"rendered_pages={len(manifest)} output={args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())