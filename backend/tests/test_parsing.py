"""
Tests for the parsing service (Phase 1).
Uses in-memory bytes fixtures so no real files need to be on disk.
"""
import io
import textwrap

import pytest

from app.services.parsing import ParseResult, parse_document


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_simple_docx(text: str) -> bytes:
    """Build a minimal DOCX in memory containing `text`."""
    import docx

    doc = docx.Document()
    for line in text.splitlines():
        doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestParseDocument:
    def test_unsupported_extension_raises(self):
        with pytest.raises(ValueError, match="Unsupported file type"):
            parse_document("resume.txt", b"some content")

    def test_docx_extracts_text(self):
        try:
            import docx  # noqa: F401
        except ImportError:
            pytest.skip("python-docx not installed")

        sample_text = textwrap.dedent("""\
            John Doe
            Software Engineer
            Skills: Python, FastAPI
        """)
        content = make_simple_docx(sample_text)
        result = parse_document("resume.docx", content)

        assert isinstance(result, ParseResult)
        assert "John Doe" in result.raw_text
        assert result.ocr_required is False

    def test_pdf_empty_content_flags_ocr(self, tmp_path):
        """
        A PDF that yields no text (e.g. scanned image) should set ocr_required=True.
        We simulate this by passing a corrupt/empty PDF.
        """
        # An almost-empty bytes stream will fail both extractors → ocr_required
        result = parse_document("scanned.pdf", b"%PDF-1.4 % fake empty pdf")
        assert result.ocr_required is True
        assert result.raw_text == ""

    def test_parse_result_dataclass(self):
        r = ParseResult(raw_text="hello world")
        assert r.raw_text == "hello world"
        assert r.ocr_required is False

        r2 = ParseResult(raw_text="", ocr_required=True)
        assert r2.ocr_required is True
