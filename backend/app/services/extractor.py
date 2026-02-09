import io
import re

from markitdown import MarkItDown, StreamInfo

# Matches two pipe-delimited table rows separated by a blank line.
# Collapses them into contiguous rows so markdown table parsers work.
_TABLE_ROW_GAP = re.compile(r"(\|[^\n]*\|)\n\n(\|)")


class ExtractorService:
    """Service for extracting structured Markdown from .docx files."""

    _DOCX_STREAM_INFO = StreamInfo(
        extension=".docx",
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    def __init__(self) -> None:
        self._md = MarkItDown()

    def extract_markdown(self, doc_bytes: bytes) -> str:
        """Converts docx bytes to Markdown string preserving document order."""
        result = self._md.convert_stream(
            io.BytesIO(doc_bytes),
            stream_info=self._DOCX_STREAM_INFO,
        )
        # Some DOCX files store tables as plain-text pipe-delimited paragraphs
        # rather than proper Word tables. This causes blank lines between rows
        # which breaks downstream markdown table parsers. Collapse them.
        return _TABLE_ROW_GAP.sub(r"\1\n\2", result.text_content)


def get_extractor_service() -> ExtractorService:
    """Dependency that provides an ExtractorService instance."""
    return ExtractorService()
