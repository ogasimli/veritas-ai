import io

from docx import Document as DocumentFactory
from docx.document import Document
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph


class ExtractorService:
    """Service for extracting structured Markdown from .docx files."""

    def extract_markdown(self, doc_bytes: bytes) -> str:
        """Converts docx bytes to Markdown string preserving document order."""
        doc = DocumentFactory(io.BytesIO(doc_bytes))
        markdown_parts = []

        for block in self._iter_block_items(doc):
            if isinstance(block, Paragraph):
                text = block.text.strip()
                if text:
                    level = self._get_heading_level(block)
                    if level > 0:
                        markdown_parts.append(f"{'#' * level} {text}")
                    else:
                        markdown_parts.append(text)
            elif isinstance(block, Table):
                table_md = self._table_to_markdown(block)
                if table_md:
                    markdown_parts.append(table_md)

        return "\n\n".join(markdown_parts)

    def _iter_block_items(self, parent):
        """Yields each paragraph and table child within parent, in document order."""
        if isinstance(parent, Document):
            parent_elm = parent.element.body
        else:
            raise ValueError("Unsupported parent type")

        for child in parent_elm.iterchildren():
            if isinstance(child, CT_P):
                yield Paragraph(child, parent)
            elif isinstance(child, CT_Tbl):
                yield Table(child, parent)

    def _get_heading_level(self, paragraph: Paragraph) -> int:
        """Determines if a paragraph is a heading and returns its level."""
        try:
            style_name = paragraph.style.name
            if style_name and style_name.startswith("Heading"):
                # Handle 'Heading 1', 'Heading 2', etc.
                parts = style_name.split()
                if len(parts) > 1 and parts[-1].isdigit():
                    return int(parts[-1])
                return 1
        except (AttributeError, ValueError):
            pass
        return 0

    def _table_to_markdown(self, table: Table) -> str:
        """Converts a docx Table object to a Markdown table string."""
        # Extract row data
        raw_rows = []
        for row in table.rows:
            # Clean cells: remove newlines and leading/trailing whitespace
            cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
            raw_rows.append(cells)

        if not raw_rows or not raw_rows[0]:
            return ""

        # Markdown table structure
        md_lines = []

        # Header row
        md_lines.append("| " + " | ".join(raw_rows[0]) + " |")

        # Alignment/Separator row
        md_lines.append("| " + " | ".join(["---"] * len(raw_rows[0])) + " |")

        # Data rows
        for row in raw_rows[1:]:
            # Ensure row has same number of cells as header (fill missing with empty)
            row_cells = row + [""] * (len(raw_rows[0]) - len(row))
            md_lines.append("| " + " | ".join(row_cells[: len(raw_rows[0])]) + " |")

        return "\n".join(md_lines)


def get_extractor_service() -> ExtractorService:
    """Dependency that provides an ExtractorService instance."""
    return ExtractorService()
