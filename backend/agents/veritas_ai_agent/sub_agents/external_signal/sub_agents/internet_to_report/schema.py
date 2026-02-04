"""Schema for internet-to-report verification output."""

from typing import Literal

from pydantic import BaseModel, Field

from veritas_ai_agent.schemas import BaseAgentOutput


class CompanyProfile(BaseModel):
    """Company identification and scope extracted from financial statements."""

    legal_name: str = Field(description="Legal entity name from financial statement")
    alternative_names: list[str] = Field(
        default_factory=list,
        description="Alternative names, brands, or trading names",
    )
    jurisdiction: str = Field(
        default="", description="Country/jurisdiction of incorporation"
    )
    website: str = Field(
        default="", description="Company website or domain if available"
    )
    registration_number: str = Field(
        default="", description="Company registration number if disclosed"
    )
    ticker_isin: str = Field(
        default="", description="Stock ticker or ISIN if available"
    )
    subsidiaries: list[str] = Field(
        default_factory=list,
        description="Names of subsidiaries, associates, or joint ventures",
    )
    shareholders: list[str] = Field(
        default_factory=list,
        description="Shareholders, ultimate parent, or UBO if disclosed",
    )
    key_management: list[str] = Field(
        default_factory=list,
        description="CEO, CFO, Board members, or signatories",
    )
    material_counterparties: list[str] = Field(
        default_factory=list,
        description="Key customers, suppliers, lenders, guarantors if significant",
    )
    industry_sector: str = Field(
        default="", description="Industry or sector of operations"
    )
    business_context: str = Field(
        default="",
        description="Revenue drivers, geographic footprint, key assets/projects, applicable regulations",
    )


class ResearchWindow(BaseModel):
    """Temporal scope for external signal research."""

    fiscal_year: str = Field(description="Reporting period (fiscal year)")
    reporting_date: str = Field(description="Balance sheet date (YYYY-MM-DD)")
    fs_issue_date: str | None = Field(
        default=None,
        description="Financial statement authorization/issue date if present (YYYY-MM-DD)",
    )
    subsequent_period_start: str = Field(
        description="Start of subsequent period (reporting date)"
    )
    subsequent_period_end: str = Field(
        description="End of subsequent period (fs_issue_date or reporting_date + 120 days)"
    )
    assumption_used: bool = Field(
        default=False,
        description="True if +120 days default was used because FS issue date unavailable",
    )


class ExternalSignalSource(BaseModel):
    """Source information for an external signal."""

    url: str = Field(description="Direct URL to source")
    publisher: str = Field(description="Publisher or source name")


class ExternalSignalFinding(BaseModel):
    """A risk signal found through external search."""

    signal_title: str = Field(description="Short title summarizing the signal")
    signal_type: list[
        Literal[
            "news",
            "legal_regulatory",
            "financing_distress",
            "contracts_tenders",
            "ownership_governance",
            "industry_market",
        ]
    ] = Field(description="Type(s) of signal detected (can be multiple)")
    entities_involved: list[str] = Field(
        description="Company, subsidiary, JV, or counterparty names involved"
    )
    event_date: str = Field(
        description="Event date or best estimate (YYYY-MM-DD format, empty if unknown)"
    )
    sources: list[ExternalSignalSource] = Field(
        description="List of sources with URLs and publishers"
    )
    summary: str = Field(
        description="Factual summary of the signal (2-3 sentences, no speculation)"
    )


class ExternalSignalInternetToReportOutput(BaseAgentOutput):
    """Output from internet-to-report agent - external signals that may contradict report."""

    company_profile: CompanyProfile | None = Field(
        default=None, description="Extracted company identification and scope"
    )
    research_window: ResearchWindow | None = Field(
        default=None, description="Temporal scope for research"
    )
    findings: list[ExternalSignalFinding] = Field(
        default_factory=list,
        description="External risk signals discovered through Deep Research",
    )
