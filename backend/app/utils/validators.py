"""Validation utilities for document content."""

import re


def is_financial_document(markdown_text: str) -> tuple[bool, float]:
    """
    Determine if the provided markdown text is a financial document.

    This function uses regex patterns to detect financial statement indicators
    and calculates a confidence score based on the presence of various
    financial terms and patterns.

    Args:
        markdown_text: The markdown text to analyze

    Returns:
        A tuple containing:
            - is_financial (bool): True if confidence score >= 0.4, False otherwise
            - confidence_score (float): A score between 0.0 and 1.0 indicating
              the likelihood that this is a financial document

    Examples:
        >>> is_financial_document("Balance Sheet as of December 31, 2023...")
        (True, 0.65)
        >>> is_financial_document("Once upon a time in a faraway land...")
        (False, 0.0)
    """
    if not markdown_text or not isinstance(markdown_text, str):
        return False, 0.0

    # Convert to lowercase for case-insensitive matching
    text_lower = markdown_text.lower()

    # Track weighted indicators
    indicators = []

    # Pattern 1: Financial statement types (high weight)
    financial_statement_patterns = [
        r'\bbalance\s+sheet\b',
        r'\bincome\s+statement\b',
        r'\bcash\s+flow\s+statement\b',
        r'\bstatement\s+of\s+cash\s+flows\b',
        r'\bprofit\s+and\s+loss\b',
        r'\bp\s*&\s*l\b',
        r'\bstatement\s+of\s+financial\s+position\b',
        r'\bstatement\s+of\s+comprehensive\s+income\b',
        r'\bstatement\s+of\s+changes\s+in\s+equity\b',
    ]
    for pattern in financial_statement_patterns:
        if re.search(pattern, text_lower):
            indicators.append(0.25)  # High weight
            break  # Count only once for this category

    # Pattern 2: Accounting standards (high weight)
    accounting_standards_patterns = [
        r'\bifrs\b',
        r'\bias\s+\d+\b',
        r'\bgaap\b',
        r'\bus\s+gaap\b',
        r'\baccounting\s+standards\b',
        r'\bfinancial\s+reporting\s+standards\b',
    ]
    for pattern in accounting_standards_patterns:
        if re.search(pattern, text_lower):
            indicators.append(0.20)  # High weight
            break  # Count only once for this category

    # Pattern 3: Audit terms (medium weight)
    audit_patterns = [
        r'\baudit\s+report\b',
        r'\bexternal\s+audit\b',
        r'\binternal\s+audit\b',
        r'\bauditor\b',
        r'\bopinion\s+of\s+the\s+auditors\b',
        r'\bqualified\s+opinion\b',
        r'\bunqualified\s+opinion\b',
    ]
    for pattern in audit_patterns:
        if re.search(pattern, text_lower):
            indicators.append(0.15)  # Medium weight
            break  # Count only once for this category

    # Pattern 4: Financial terms - assets, liabilities, equity (medium weight)
    balance_sheet_terms = [
        r'\btotal\s+assets\b',
        r'\bcurrent\s+assets\b',
        r'\bnon-current\s+assets\b',
        r'\btotal\s+liabilities\b',
        r'\bcurrent\s+liabilities\b',
        r'\bnon-current\s+liabilities\b',
        r'\bshareholders?\s+equity\b',
        r'\bretained\s+earnings\b',
    ]
    balance_sheet_count = sum(
        1 for pattern in balance_sheet_terms if re.search(pattern, text_lower)
    )
    if balance_sheet_count >= 3:
        indicators.append(0.20)
    elif balance_sheet_count >= 1:
        indicators.append(0.10)

    # Pattern 5: Income statement terms (medium weight)
    income_statement_terms = [
        r'\brevenue\b',
        r'\bgross\s+profit\b',
        r'\boperating\s+income\b',
        r'\bnet\s+income\b',
        r'\bearnings\s+per\s+share\b',
        r'\bebitda\b',
        r'\bebit\b',
        r'\bcost\s+of\s+goods\s+sold\b',
        r'\boperating\s+expenses\b',
    ]
    income_statement_count = sum(
        1 for pattern in income_statement_terms if re.search(pattern, text_lower)
    )
    if income_statement_count >= 3:
        indicators.append(0.20)
    elif income_statement_count >= 1:
        indicators.append(0.10)

    # Pattern 6: Currency amounts (medium weight)
    # Matches patterns like: $1,234 or $1,234.56 or 1,234.56 USD/EUR/GBP
    currency_patterns = [
        r'\$\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?',  # $X,XXX or $X,XXX.XX
        r'\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s*(?:USD|EUR|GBP|CAD|AUD)\b',  # XXX.XX USD
        r'[€£¥]\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?',  # €X,XXX or £X,XXX
    ]
    currency_matches = sum(
        len(re.findall(pattern, markdown_text)) for pattern in currency_patterns
    )
    if currency_matches >= 10:
        indicators.append(0.15)
    elif currency_matches >= 5:
        indicators.append(0.10)
    elif currency_matches >= 1:
        indicators.append(0.05)

    # Pattern 7: Fiscal/reporting periods (low weight)
    period_patterns = [
        r'\bfiscal\s+year\b',
        r'\bfiscal\s+quarter\b',
        r'\bannual\s+report\b',
        r'\bquarterly\s+report\b',
        r'\bfor\s+the\s+year\s+ended\b',
        r'\bas\s+of\s+(?:december|march|june|september)\s+\d{1,2},?\s+\d{4}\b',
        r'\bfy\s*\d{4}\b',
        r'\bq[1-4]\s+\d{4}\b',
    ]
    for pattern in period_patterns:
        if re.search(pattern, text_lower):
            indicators.append(0.10)
            break  # Count only once for this category

    # Calculate confidence score (capped at 1.0)
    confidence_score = min(sum(indicators), 1.0)

    # Threshold for classification
    threshold = 0.4
    is_financial = confidence_score >= threshold

    return is_financial, confidence_score
