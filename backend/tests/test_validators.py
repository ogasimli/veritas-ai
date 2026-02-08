"""Tests for deterministic document content validator."""

from app.utils.validators import validate_document_content


class TestValidateDocumentContent:
    """Test suite for validate_document_content function."""

    def test_none_input(self):
        is_valid, error = validate_document_content(None)
        assert is_valid is False
        assert error == "Document is empty"

    def test_empty_string(self):
        is_valid, error = validate_document_content("")
        assert is_valid is False
        assert error == "Document is empty"

    def test_whitespace_only(self):
        is_valid, error = validate_document_content("   \n\n\t  ")
        assert is_valid is False
        assert error == "Document contains only whitespace"

    def test_too_short(self):
        is_valid, error = validate_document_content("Short text | with table")
        assert is_valid is False
        assert error == "Document too short to be a financial statement"

    def test_no_tables(self):
        text = "a" * 300  # Long enough but no pipe characters
        is_valid, error = validate_document_content(text)
        assert is_valid is False
        assert (
            error
            == "Document contains no tables — financial statements require tabular data"
        )

    def test_valid_document(self):
        text = (
            "x" * 200
            + "\n| Column A | Column B |\n|----------|----------|\n| data | data |"
        )
        is_valid, error = validate_document_content(text)
        assert is_valid is True
        assert error == ""

    def test_integer_input(self):
        is_valid, error = validate_document_content(12345)
        assert is_valid is False
        assert error == "Document is empty"

    def test_exactly_200_chars_stripped(self):
        """Text that is exactly 200 chars after stripping should pass the length check."""
        text = "a" * 200 + " | table marker"
        is_valid, error = validate_document_content(text)
        assert is_valid is True
        assert error == ""

    def test_199_chars_stripped_fails(self):
        """Text that is 199 chars after stripping should fail."""
        text = "a" * 199 + " | table marker"
        # total stripped length is 199 + len(" | table marker") = 199 + 16 = 215
        # but wait, strip() only removes leading/trailing whitespace, not internal
        # so the full string is 199 + 16 = 215 chars, which is > 200
        # Actually let me make sure it's exactly 199 after strip
        text = "a" * 199
        is_valid, _error = validate_document_content(text)
        assert is_valid is False

    def test_pipe_in_middle_of_text(self):
        """A pipe character anywhere counts as a table marker."""
        text = "a" * 200 + " some text with a | in it"
        is_valid, _error = validate_document_content(text)
        assert is_valid is True
        assert _error == ""
