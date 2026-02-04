"""Unit tests for the aggregator callback."""

import pytest

from veritas_ai_agent.sub_agents.external_signal.sub_agents.aggregator.callbacks import (
    after_aggregator_callback,
)
from veritas_ai_agent.sub_agents.external_signal.sub_agents.aggregator.schema import (
    EvidenceInFS,
    ExpectedFSImpact,
    ExternalSignalFindingsAggregatorOutput,
    ReconciledExternalSignal,
)
from veritas_ai_agent.sub_agents.external_signal.sub_agents.report_to_internet.schema import (
    ExternalSignalClaimVerification,
    ExternalSignalReportToInternetOutput,
)


@pytest.fixture
def mock_callback_context():
    """Create a mock callback context with state."""

    class MockCallbackContext:
        def __init__(self):
            self.state = {}

    return MockCallbackContext()


@pytest.mark.asyncio
async def test_callback_with_full_data(mock_callback_context):
    """Test callback with both external signals and claim verifications."""
    # Setup external signals (from aggregator LLM output)
    signal1 = ReconciledExternalSignal(
        signal_title="Lawsuit filed",
        signal_type=["legal_regulatory"],
        entities_involved=["Company A"],
        event_date="2025-01-15",
        sources=[{"url": "http://example.com", "publisher": "Reuters"}],
        summary="Major lawsuit filed",
        expected_fs_impact=ExpectedFSImpact(
            area=["Notes"], notes_expected=["Contingencies"], rationale="Legal matter"
        ),
        evidence_in_fs=EvidenceInFS(
            reflected_in_fs="No",
            search_terms_used=["lawsuit", "litigation"],
            not_found_statement="No mention found",
        ),
        gap_classification="POTENTIAL_OMISSION",
        severity="high",
    )

    signal2 = ReconciledExternalSignal(
        signal_title="Already disclosed event",
        signal_type=["news"],
        entities_involved=["Company A"],
        event_date="2025-02-01",
        sources=[{"url": "http://example.com/2", "publisher": "Bloomberg"}],
        summary="Event already in FS",
        expected_fs_impact=ExpectedFSImpact(
            area=["Notes"], notes_expected=["Events"], rationale="Disclosed"
        ),
        evidence_in_fs=EvidenceInFS(
            reflected_in_fs="Yes",
            search_terms_used=["event"],
            not_found_statement="",
        ),
        gap_classification="POTENTIAL_OMISSION",
        severity="low",
    )

    aggregator_output = ExternalSignalFindingsAggregatorOutput(
        external_signals=[signal1, signal2],
        claim_verifications=[],  # Will be populated from state
    )

    # Setup claim verifications (from report_to_internet output)
    verification1 = ExternalSignalClaimVerification(
        claim_text="Founded in 2020",
        claim_category="incorporation",
        verification_status="CONTRADICTED",
        evidence_summary="Actually founded in 2019",
        source_urls=["http://example.com/verify1"],
        discrepancy="Date mismatch",
    )

    verification2 = ExternalSignalClaimVerification(
        claim_text="Located in NYC",
        claim_category="location",
        verification_status="VERIFIED",
        evidence_summary="Confirmed",
        source_urls=["http://example.com/verify2"],
        discrepancy="",  # No discrepancy, should be filtered
    )

    verification3 = ExternalSignalClaimVerification(
        claim_text="Has 100 employees",
        claim_category="headcount",
        verification_status="CANNOT_VERIFY",
        evidence_summary="No data found",
        source_urls=[],
        discrepancy="",
    )

    report_to_internet_output = ExternalSignalReportToInternetOutput(
        verifications=[verification1, verification2, verification3]
    )

    # Setup state
    mock_callback_context.state = {
        "external_signal_findings_aggregator_output": aggregator_output,
        "external_signal_report_to_internet_output": report_to_internet_output,
    }

    # Execute callback
    await after_aggregator_callback(mock_callback_context)

    # Verify results
    result = mock_callback_context.state["external_signal_findings_aggregator_output"]

    # Should have 1 external signal (signal2 filtered because reflected_in_fs="Yes")
    assert len(result.external_signals) == 1
    assert result.external_signals[0].signal_title == "Lawsuit filed"

    # Should have 2 claim verifications (verification2 filtered because VERIFIED + no discrepancy)
    assert len(result.claim_verifications) == 2

    # Check severity assignments
    contradicted = next(
        v for v in result.claim_verifications if v.verification_status == "CONTRADICTED"
    )
    assert contradicted.severity == "high"

    cannot_verify = next(
        v
        for v in result.claim_verifications
        if v.verification_status == "CANNOT_VERIFY"
    )
    assert cannot_verify.severity == "medium"

    # Check sorting (high before medium)
    assert result.claim_verifications[0].severity == "high"
    assert result.claim_verifications[1].severity == "medium"


@pytest.mark.asyncio
async def test_callback_filters_verified_with_discrepancy(mock_callback_context):
    """Test that VERIFIED claims WITH discrepancies are kept."""
    verification = ExternalSignalClaimVerification(
        claim_text="Revenue $1M",
        claim_category="financials",
        verification_status="VERIFIED",
        evidence_summary="Confirmed but timing off",
        source_urls=["http://example.com"],
        discrepancy="Q1 vs Q2 discrepancy",  # Has discrepancy, should be kept
    )

    report_to_internet_output = ExternalSignalReportToInternetOutput(
        verifications=[verification]
    )

    aggregator_output = ExternalSignalFindingsAggregatorOutput(
        external_signals=[], claim_verifications=[]
    )

    mock_callback_context.state = {
        "external_signal_findings_aggregator_output": aggregator_output,
        "external_signal_report_to_internet_output": report_to_internet_output,
    }

    await after_aggregator_callback(mock_callback_context)

    result = mock_callback_context.state["external_signal_findings_aggregator_output"]

    # Should keep the verification because it has a discrepancy
    assert len(result.claim_verifications) == 1
    assert result.claim_verifications[0].severity == "low"  # VERIFIED → low


@pytest.mark.asyncio
async def test_callback_filters_unclear_external_signals(mock_callback_context):
    """Test that external signals with reflected_in_fs='Unclear' are kept."""
    signal = ReconciledExternalSignal(
        signal_title="Unclear event",
        signal_type=["news"],
        entities_involved=["Company A"],
        event_date="2025-03-01",
        sources=[{"url": "http://example.com", "publisher": "Reuters"}],
        summary="Event with unclear disclosure",
        expected_fs_impact=ExpectedFSImpact(
            area=["Notes"], notes_expected=["Events"], rationale="May be relevant"
        ),
        evidence_in_fs=EvidenceInFS(
            reflected_in_fs="Unclear",
            search_terms_used=["event"],
            not_found_statement="Ambiguous mention",
        ),
        gap_classification="NEEDS_JUDGMENT",
        severity="medium",
    )

    aggregator_output = ExternalSignalFindingsAggregatorOutput(
        external_signals=[signal], claim_verifications=[]
    )

    mock_callback_context.state = {
        "external_signal_findings_aggregator_output": aggregator_output,
        "external_signal_report_to_internet_output": None,
    }

    await after_aggregator_callback(mock_callback_context)

    result = mock_callback_context.state["external_signal_findings_aggregator_output"]

    # Should keep signal with "Unclear" status
    assert len(result.external_signals) == 1
    assert result.external_signals[0].evidence_in_fs.reflected_in_fs == "Unclear"


@pytest.mark.asyncio
async def test_callback_sorting_by_severity(mock_callback_context):
    """Test that findings are correctly sorted by severity."""
    # Create signals with different severities (out of order)
    signal_low = ReconciledExternalSignal(
        signal_title="Low severity",
        signal_type=["news"],
        entities_involved=["Company A"],
        event_date="2025-01-01",
        sources=[{"url": "http://example.com/1", "publisher": "Reuters"}],
        summary="Minor news",
        expected_fs_impact=ExpectedFSImpact(
            area=["Notes"], notes_expected=["Events"], rationale="Minor"
        ),
        evidence_in_fs=EvidenceInFS(
            reflected_in_fs="No", search_terms_used=["news"], not_found_statement=""
        ),
        gap_classification="NEEDS_JUDGMENT",
        severity="low",
    )

    signal_high = ReconciledExternalSignal(
        signal_title="High severity",
        signal_type=["legal_regulatory"],
        entities_involved=["Company A"],
        event_date="2025-02-01",
        sources=[{"url": "http://example.com/2", "publisher": "Reuters"}],
        summary="Major lawsuit",
        expected_fs_impact=ExpectedFSImpact(
            area=["Notes"], notes_expected=["Contingencies"], rationale="Material"
        ),
        evidence_in_fs=EvidenceInFS(
            reflected_in_fs="No", search_terms_used=["lawsuit"], not_found_statement=""
        ),
        gap_classification="POTENTIAL_CONTRADICTION",
        severity="high",
    )

    signal_medium = ReconciledExternalSignal(
        signal_title="Medium severity",
        signal_type=["financing_distress"],
        entities_involved=["Company A"],
        event_date="2025-03-01",
        sources=[{"url": "http://example.com/3", "publisher": "Reuters"}],
        summary="Rating downgrade",
        expected_fs_impact=ExpectedFSImpact(
            area=["Notes"], notes_expected=["Debt"], rationale="Relevant"
        ),
        evidence_in_fs=EvidenceInFS(
            reflected_in_fs="No", search_terms_used=["rating"], not_found_statement=""
        ),
        gap_classification="POTENTIAL_OMISSION",
        severity="medium",
    )

    # Add in random order
    aggregator_output = ExternalSignalFindingsAggregatorOutput(
        external_signals=[signal_low, signal_high, signal_medium],
        claim_verifications=[],
    )

    mock_callback_context.state = {
        "external_signal_findings_aggregator_output": aggregator_output,
        "external_signal_report_to_internet_output": None,
    }

    await after_aggregator_callback(mock_callback_context)

    result = mock_callback_context.state["external_signal_findings_aggregator_output"]

    # Should be sorted: high, medium, low
    assert len(result.external_signals) == 3
    assert result.external_signals[0].severity == "high"
    assert result.external_signals[1].severity == "medium"
    assert result.external_signals[2].severity == "low"


@pytest.mark.asyncio
async def test_callback_handles_missing_aggregator_output(mock_callback_context):
    """Test callback gracefully handles missing aggregator output."""
    mock_callback_context.state = {}

    # Should not raise an exception
    await after_aggregator_callback(mock_callback_context)

    # State should remain empty
    assert (
        "external_signal_findings_aggregator_output" not in mock_callback_context.state
    )


@pytest.mark.asyncio
async def test_callback_handles_missing_report_to_internet(mock_callback_context):
    """Test callback handles missing report_to_internet output."""
    signal = ReconciledExternalSignal(
        signal_title="Test signal",
        signal_type=["news"],
        entities_involved=["Company A"],
        event_date="2025-01-01",
        sources=[{"url": "http://example.com", "publisher": "Reuters"}],
        summary="Test",
        expected_fs_impact=ExpectedFSImpact(
            area=["Notes"], notes_expected=["Events"], rationale="Test"
        ),
        evidence_in_fs=EvidenceInFS(
            reflected_in_fs="No", search_terms_used=["test"], not_found_statement=""
        ),
        gap_classification="POTENTIAL_OMISSION",
        severity="medium",
    )

    aggregator_output = ExternalSignalFindingsAggregatorOutput(
        external_signals=[signal], claim_verifications=[]
    )

    mock_callback_context.state = {
        "external_signal_findings_aggregator_output": aggregator_output,
        # No report_to_internet_output
    }

    await after_aggregator_callback(mock_callback_context)

    result = mock_callback_context.state["external_signal_findings_aggregator_output"]

    # Should have external signals but no claim verifications
    assert len(result.external_signals) == 1
    assert len(result.claim_verifications) == 0


@pytest.mark.asyncio
async def test_callback_with_empty_lists(mock_callback_context):
    """Test callback with empty external signals and verifications."""
    aggregator_output = ExternalSignalFindingsAggregatorOutput(
        external_signals=[], claim_verifications=[]
    )

    report_to_internet_output = ExternalSignalReportToInternetOutput(verifications=[])

    mock_callback_context.state = {
        "external_signal_findings_aggregator_output": aggregator_output,
        "external_signal_report_to_internet_output": report_to_internet_output,
    }

    await after_aggregator_callback(mock_callback_context)

    result = mock_callback_context.state["external_signal_findings_aggregator_output"]

    # Should have empty lists
    assert len(result.external_signals) == 0
    assert len(result.claim_verifications) == 0


@pytest.mark.asyncio
async def test_callback_preserves_error_field(mock_callback_context):
    """Test that callback preserves the error field from aggregator output."""
    from veritas_ai_agent.schemas import AgentError

    aggregator_output = ExternalSignalFindingsAggregatorOutput(
        error=AgentError(
            agent_name="ExternalSignalFindingsAggregator",
            error_type="test_error",
            error_message="Test error message",
        ),
        external_signals=[],
        claim_verifications=[],
    )

    mock_callback_context.state = {
        "external_signal_findings_aggregator_output": aggregator_output,
    }

    await after_aggregator_callback(mock_callback_context)

    result = mock_callback_context.state["external_signal_findings_aggregator_output"]

    # Should preserve error field
    assert result.error is not None
    assert result.error.error_message == "Test error message"


@pytest.mark.asyncio
async def test_callback_handles_report_output_without_verifications_attr(
    mock_callback_context,
):
    """Test callback handles report_to_internet output without verifications attribute."""

    class FakeOutput:
        """Mock output without verifications attribute."""

        pass

    aggregator_output = ExternalSignalFindingsAggregatorOutput(
        external_signals=[], claim_verifications=[]
    )

    mock_callback_context.state = {
        "external_signal_findings_aggregator_output": aggregator_output,
        "external_signal_report_to_internet_output": FakeOutput(),
    }

    # Should not raise an exception
    await after_aggregator_callback(mock_callback_context)

    result = mock_callback_context.state["external_signal_findings_aggregator_output"]
    assert len(result.claim_verifications) == 0
