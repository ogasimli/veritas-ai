"""Deterministic pre-flight validation for document content."""


def validate_document_content(markdown_text: str) -> tuple[bool, str]:
    """
    Deterministic pre-flight checks for obviously invalid documents.
    Returns (is_valid, error_message). error_message is empty when valid.
    """
    if not isinstance(markdown_text, str):
        return False, "Document is empty"

    if len(markdown_text) == 0:
        return False, "Document is empty"

    if markdown_text.strip() == "":
        return False, "Document contains only whitespace"

    if len(markdown_text.strip()) < 200:
        return False, "Document too short to be a financial statement"

    if "|" not in markdown_text:
        return False, "Document contains no tables — financial statements require tabular data"

    return True, ""
