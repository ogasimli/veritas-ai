from typing import Literal

from pydantic import BaseModel, Field

from veritas_ai_agent.schemas import BaseAgentOutput


class ExpectedFSImpact(BaseModel):
    """Expected financial statement impact for an external signal."""

    area: list[str] = Field(
        description="FS areas where impact expected (e.g., 'BS', 'P&L', 'CF', 'Notes')"
    )
    notes_expected: list[str] = Field(
        description="Specific note types expected (e.g., 'Contingencies', 'Subsequent events', 'Related parties')"
    )
    rationale: str = Field(
        description="Explanation of why this signal should appear in FS"
    )


class EvidenceInFS(BaseModel):
    """Evidence of signal reflection in financial statements."""

    reflected_in_fs: Literal["Yes", "No", "Unclear"] = Field(
        description="Whether the signal is reflected in the financial statements"
    )
    search_terms_used: list[str] = Field(
        description="Terms used to search FS for corroboration"
    )
    not_found_statement: str = Field(
        default="",
        description="Explanation if not found or unclear (empty if reflected)",
    )


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
    sources: list[dict[str, str]] = Field(
        description="List of sources with url and publisher"
    )
    summary: str = Field(description="Factual summary (2-3 sentences)")

    # Reconciliation fields (populated by aggregator)
    expected_fs_impact: ExpectedFSImpact = Field(
        description="Expected FS impact for this signal"
    )
    evidence_in_fs: EvidenceInFS = Field(description="Evidence of reflection in FS")
    gap_classification: Literal[
        "POTENTIAL_OMISSION", "POTENTIAL_CONTRADICTION", "NEEDS_JUDGMENT"
    ] = Field(description="Gap classification after FS reconciliation")

    # Severity (set by aggregator based on gap classification)
    severity: Literal["high", "medium", "low"] = Field(
        description="Severity level based on materiality and risk"
    )


class ReconciledClaimVerification(BaseModel):
    """
    Claim verification from report-to-internet.

    This represents a claim extracted from the financial statement
    that has been verified against internet sources.
    """

    claim_text: str = Field(description="The claim from the financial statement")
    claim_category: str = Field(description="Classification of the claim")
    verification_status: Literal["VERIFIED", "CONTRADICTED", "CANNOT_VERIFY"] = Field(
        description="Verification result from Deep Research"
    )
    evidence_summary: str = Field(description="What was found online")
    source_urls: list[str] = Field(description="Supporting URLs")
    discrepancy: str = Field(
        default="", description="Any discrepancies found (dates off, wording, etc.)"
    )

    # Severity (set by aggregator based on verification status)
    severity: Literal["high", "medium", "low"] = Field(
        description="Severity level: high=CONTRADICTED, medium=CANNOT_VERIFY, low=VERIFIED"
    )


class ExternalSignalFindingsAggregatorOutput(BaseAgentOutput):
    """
    Output schema for the external signal aggregator agent.

    Contains two separate lists for the two fundamentally different finding types:
    - external_signals: Findings from internet research reconciled with FS
    - claim_verifications: FS claims verified against internet sources
    """

    external_signals: list[ReconciledExternalSignal] = Field(
        default_factory=list,
        description="External signals found via internet research, reconciled with FS (from internet_to_report)",
    )
    claim_verifications: list[ReconciledClaimVerification] = Field(
        default_factory=list,
        description="Financial statement claims verified against internet (from report_to_internet)",
    )
