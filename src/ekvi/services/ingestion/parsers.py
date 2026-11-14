"""Document parsers producing ContentBlock records with location evidence.

MVP formats (ARCH §14): PDF, DOCX, XLSX, CSV, TXT/Markdown.
OCR hooks are present but optional; uncertain content is flagged.
"""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass, field
from typing import Any, Optional

from pypdf import PdfReader
from docx import Document as DocxDocument
import openpyxl
import pandas as pd


@dataclass
class ParsedBlock:
    block_type: str
    text: str
    page: Optional[int] = None
    section: Optional[str] = None
    paragraph_index: Optional[int] = None
    table_ref: Optional[str] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    extraction_confidence: float = 1.0
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParseResult:
    blocks: list[ParsedBlock]
    warnings: list[str] = field(default_factory=list)
    quality: dict[str, Any] = field(default_factory=dict)


def checksum_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_pdf(data: bytes) -> ParseResult:
    reader = PdfReader(io.BytesIO(data))
    blocks: list[ParsedBlock] = []
    warnings: list[str] = []
    for i, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"page {i}: extract failed ({exc})")
            continue
        if not text.strip():
            warnings.append(f"page {i}: empty or image-only (OCR not applied in prototype)")
            blocks.append(
                ParsedBlock(
                    block_type="page",
                    text="",
                    page=i,
                    extraction_confidence=0.2,
                    extra={"needs_ocr": True},
                )
            )
            continue
        for j, para in enumerate(text.split("\n\n")):
            para = para.strip()
            if para:
                blocks.append(
                    ParsedBlock(
                        block_type="paragraph",
                        text=para,
                        page=i,
                        paragraph_index=j,
                        extraction_confidence=0.9,
                    )
                )
    return ParseResult(
        blocks=blocks,
        warnings=warnings,
        quality={"pages": len(reader.pages), "blocks": len(blocks)},
    )


def parse_docx(data: bytes) -> ParseResult:
    doc = DocxDocument(io.BytesIO(data))
    blocks: list[ParsedBlock] = []
    current_heading = None
    for i, para in enumerate(doc.paragraphs):
        style = para.style.name if para.style else ""
        text = para.text.strip()
        if not text:
            continue
        if style.startswith("Heading"):
            current_heading = text
            blocks.append(
                ParsedBlock(
                    block_type="heading",
                    text=text,
                    section=text,
                    paragraph_index=i,
                    extraction_confidence=1.0,
                    extra={"style": style},
                )
            )
        else:
            blocks.append(
                ParsedBlock(
                    block_type="paragraph",
                    text=text,
                    section=current_heading,
                    paragraph_index=i,
                    extraction_confidence=1.0,
                )
            )
    for t_idx, table in enumerate(doc.tables):
        rows = []
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells]
            rows.append(" | ".join(cells))
        table_text = "\n".join(rows)
        blocks.append(
            ParsedBlock(
                block_type="table",
                text=table_text,
                table_ref=f"table-{t_idx}",
                extraction_confidence=0.95,
            )
        )
    return ParseResult(blocks=blocks, quality={"paragraphs": len(doc.paragraphs), "tables": len(doc.tables)})


def parse_xlsx(data: bytes) -> ParseResult:
    wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True)
    blocks: list[ParsedBlock] = []
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        for row_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
            cells = [str(c) if c is not None else "" for c in row]
            if not any(cells):
                continue
            text = " | ".join(cells)
            blocks.append(
                ParsedBlock(
                    block_type="row",
                    text=text,
                    section=sheet_name,
                    paragraph_index=row_idx,
                    table_ref=f"{sheet_name}!R{row_idx}",
                    extraction_confidence=1.0,
                )
            )
    return ParseResult(blocks=blocks, quality={"sheets": len(wb.sheetnames), "rows": len(blocks)})


def parse_csv(data: bytes) -> ParseResult:
    df = pd.read_csv(io.BytesIO(data))
    blocks: list[ParsedBlock] = []
    header = " | ".join(str(c) for c in df.columns)
    blocks.append(
        ParsedBlock(block_type="header", text=header, paragraph_index=0, extraction_confidence=1.0)
    )
    for i, row in df.iterrows():
        text = " | ".join(str(v) for v in row.values)
        blocks.append(
            ParsedBlock(
                block_type="row",
                text=text,
                paragraph_index=int(i) + 1,
                extraction_confidence=1.0,
            )
        )
    return ParseResult(blocks=blocks, quality={"rows": len(df)})


def parse_text(data: bytes) -> ParseResult:
    text = data.decode("utf-8", errors="replace")
    blocks: list[ParsedBlock] = []
    for i, line in enumerate(text.splitlines()):
        line = line.strip()
        if line:
            blocks.append(
                ParsedBlock(
                    block_type="line",
                    text=line,
                    paragraph_index=i,
                    extraction_confidence=1.0,
                )
            )
    return ParseResult(blocks=blocks, quality={"lines": len(blocks)})


def parse_file(filename: str, data: bytes, mime_type: str) -> ParseResult:
    lower = filename.lower()
    if mime_type == "application/pdf" or lower.endswith(".pdf"):
        return parse_pdf(data)
    if "wordprocessingml" in mime_type or lower.endswith(".docx"):
        return parse_docx(data)
    if "spreadsheetml" in mime_type or lower.endswith(".xlsx"):
        return parse_xlsx(data)
    if mime_type == "text/csv" or lower.endswith(".csv"):
        return parse_csv(data)
    if mime_type in ("text/plain", "text/markdown") or lower.endswith((".txt", ".md")):
        return parse_text(data)
    raise ValueError(f"Unsupported file type: {mime_type} / {filename}")
