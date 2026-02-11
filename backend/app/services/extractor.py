import io

from markitdown import MarkItDown, StreamInfo


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
        return result.text_content


def get_extractor_service() -> ExtractorService:
    """Dependency that provides an ExtractorService instance."""
    return ExtractorService()
