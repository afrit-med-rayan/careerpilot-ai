"""
Document parsing service.

Extraction order:
  PDF  → pdfplumber (primary) → PyMuPDF (fallback if empty)
  DOCX → python-docx

If pdfplumber + PyMuPDF both return empty text, the file is likely a scanned image;
we flag ocr_required=True and return an empty string (OCR is out of scope for MVP).
"""

import io
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ParseResult:
    raw_text: str
    ocr_required: bool = False


def _extract_pdf_pdfplumber(content: bytes) -> str:
    """Primary PDF extractor using pdfplumber."""
    try:
        import pdfplumber

        text_parts: list[str] = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n".join(text_parts).strip()
    except Exception as exc:
        logger.warning("pdfplumber extraction failed: %s", exc)
        return ""


def _extract_pdf_pymupdf(content: bytes) -> str:
    """Fallback PDF extractor using PyMuPDF (fitz)."""
    try:
        import fitz  # PyMuPDF

        text_parts: list[str] = []
        doc = fitz.open(stream=content, filetype="pdf")
        for page in doc:
            text_parts.append(page.get_text())
        doc.close()
        return "\n".join(text_parts).strip()
    except Exception as exc:
        logger.warning("PyMuPDF extraction failed: %s", exc)
        return ""


def _extract_docx(content: bytes) -> str:
    """DOCX extractor using python-docx."""
    try:
        import docx

        doc = docx.Document(io.BytesIO(content))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs).strip()
    except Exception as exc:
        logger.warning("python-docx extraction failed: %s", exc)
        return ""


def parse_document(filename: str, content: bytes) -> ParseResult:
    """
    Extract raw text from a PDF or DOCX file.

    Args:
        filename: Original filename (used to detect file type by extension).
        content:  Raw file bytes.

    Returns:
        ParseResult with raw_text and an ocr_required flag.
    """
    ext = filename.rsplit(".", 1)[-1].lower()

    if ext == "pdf":
        text = _extract_pdf_pdfplumber(content)
        if not text:
            logger.info("pdfplumber returned empty; trying PyMuPDF fallback.")
            text = _extract_pdf_pymupdf(content)
        if not text:
            logger.warning("Both PDF extractors returned empty text — OCR may be required.")
            return ParseResult(raw_text="", ocr_required=True)
        return ParseResult(raw_text=text)

    elif ext in ("docx", "doc"):
        text = _extract_docx(content)
        return ParseResult(raw_text=text)

    else:
        raise ValueError(f"Unsupported file type: .{ext}. Only PDF and DOCX are supported.")
