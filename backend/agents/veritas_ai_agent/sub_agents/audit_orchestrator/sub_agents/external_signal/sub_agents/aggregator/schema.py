import json
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, Field


def serialize_to_json(v: Any) -> str | None:
    """Serialize dictionary or list to JSON string if needed."""
    if v is None:
        return None
    if isinstance(v, (dict, list)):
        return json.dumps(v)
    return v


JsonString = Annotated[str, BeforeValidator(serialize_to_json)]


class ReconciledExternalSignal(BaseModel):
    """
    External signal from internet-to-report with FS reconciliation.

    This represents a finding discovered through internet research that
    has been reconciled against the financial statements.
    """

    # Original signal fields
    signal_title: str = Field(description="Short title summarizing the signal")
    signal_type: list[str] = Field(
        description="Type(s) of signal (e.g., news, legal_regulatory, financing_distress)"
    )
    entities_involved: list[str] = Field(
        description="Company, subsidiary, JV, or counterparty names involved"
    )
    event_date: str = Field(description="Event date (YYYY-MM-DD, empty if unknown)")
    sources: str = Field(
        description="JSON string of list of sources, each with 'url' and 'publisher' keys"
    )
    summary: str = Field(description="Factual summary (2-3 sentences)")

    # Reconciliation fields (populated by aggregator)
    expected_fs_impact_area: list[str] = Field(
        description="FS areas where impact expected (e.g., 'BS', 'P&L', 'CF', 'Notes')"
    )
    expected_fs_impact_notes_expected: list[str] = Field(
        description="Specific note types expected (e.g., 'Contingencies', 'Subsequent events', 'Related parties')"
    )
    expected_fs_impact_rationale: str = Field(
        description="Explanation of why this signal should appear in FS"
    )
    evidence_reflected_in_fs: str = Field(
        description="Whether reflected in FS: 'Yes', 'No', or 'Unclear'"
    )
    evidence_search_terms_used: list[str] = Field(
        description="Terms used to search FS for corroboration"
    )
    evidence_not_found_statement: str = Field(
        default="",
        description="Explanation if not found or unclear (empty if reflected)",
    )
    gap_classification: str = Field(
        description="Gap classification: 'POTENTIAL_OMISSION', 'POTENTIAL_CONTRADICTION', or 'NEEDS_JUDGMENT'"
    )

    # Severity (set by aggregator based on gap classification)
    severity: str = Field(
        description="Severity level: 'high', 'medium', or 'low' based on materiality and risk"
    )


class ReconciledClaimVerification(BaseModel):
    """
    Claim verification from report-to-internet.

    This represents a claim extracted from the financial statement
    that has been verified against internet sources.
    """

    claim_text: str = Field(description="The claim from the financial statement")
    claim_category: str = Field(description="Classification of the claim")
    verification_status: str = Field(
        description="Verification result: 'VERIFIED', 'CONTRADICTED', or 'CANNOT_VERIFY'"
    )
    evidence_summary: str = Field(description="What was found online")
    source_urls: list[str] = Field(description="Supporting URLs")
    discrepancy: str = Field(
        default="", description="Any discrepancies found (dates off, wording, etc.)"
    )

    # Severity (set by aggregator based on verification status)
    severity: str = Field(
        description="Severity level: 'high' for CONTRADICTED, 'medium' for CANNOT_VERIFY, 'low' for VERIFIED"
    )


class ExternalSignalFindingsAggregatorOutput(BaseModel):
    """
    Output schema for the external signal aggregator agent.

    Contains two separate lists for the two fundamentally different finding types:
    - external_signals: Findings from internet research reconciled with FS
    - claim_verifications: FS claims verified against internet sources
    """

    external_signals: JsonString = Field(
        default="[]",
        description="JSON string of external signals found via internet research, reconciled with FS (list of ReconciledExternalSignal)",
    )
    claim_verifications: JsonString = Field(
        default="[]",
        description="JSON string of financial statement claims verified against internet (list of ReconciledClaimVerification)",
    )
    error: str | None = Field(default=None, description="Error message if agent failed")
