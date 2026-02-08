"""Unit tests for the aggregator callback."""

import json

import pytest

from veritas_ai_agent.sub_agents.audit_orchestrator.sub_agents.external_signal.sub_agents.aggregator.callbacks import (
    after_aggregator_callback,
)
from veritas_ai_agent.sub_agents.audit_orchestrator.sub_agents.external_signal.sub_agents.aggregator.schema import (
    ExternalSignalFindingsAggregatorOutput,
    ReconciledExternalSignal,
)
from veritas_ai_agent.sub_agents.audit_orchestrator.sub_agents.external_signal.sub_agents.verification.sub_agents.report_to_internet.schema import (
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
        sources=json.dumps([{"url": "http://example.com", "publisher": "Reuters"}]),
        summary="Major lawsuit filed",
        expected_fs_impact_area=["Notes"],
        expected_fs_impact_notes_expected=["Contingencies"],
        expected_fs_impact_rationale="Legal matter",
        evidence_reflected_in_fs="No",
        evidence_search_terms_used=["lawsuit", "litigation"],
        evidence_not_found_statement="No mention found",
        gap_classification="POTENTIAL_OMISSION",
        severity="high",
    )

    signal2 = ReconciledExternalSignal(
        signal_title="Already disclosed event",
        signal_type=["news"],
        entities_involved=["Company A"],
        event_date="2025-02-01",
        sources=json.dumps([{"url": "http://example.com/2", "publisher": "Bloomberg"}]),
        summary="Event already in FS",
        expected_fs_impact_area=["Notes"],
        expected_fs_impact_notes_expected=["Events"],
        expected_fs_impact_rationale="Disclosed",
        evidence_reflected_in_fs="Yes",
        evidence_search_terms_used=["event"],
        evidence_not_found_statement="",
        gap_classification="POTENTIAL_OMISSION",
        severity="low",
    )

    aggregator_output = ExternalSignalFindingsAggregatorOutput(
        external_signals=json.dumps([signal1.model_dump(), signal2.model_dump()]),
        claim_verifications="[]",  # Will be populated from state
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
        verifications=json.dumps(
            [
                verification1.model_dump(),
                verification2.model_dump(),
                verification3.model_dump(),
            ]
        )
    )

    # Setup state
    mock_callback_context.state = {
        "external_signal_findings_aggregator_output": aggregator_output,
        "external_signal_report_to_internet_output": report_to_internet_output,
    }

    # Execute callback
    await after_aggregator_callback(mock_callback_context)

    # Verify results (raw dictionary since .model_dump() is used in callback)
    result_dict = mock_callback_context.state[
        "external_signal_findings_aggregator_output"
    ]

    # Parse back the JSON string fields to verify contents
    result_signals = json.loads(result_dict["external_signals"])
    result_verifications = json.loads(result_dict["claim_verifications"])

    # Should have 1 external signal (signal2 filtered because reflected_in_fs="Yes")
    assert len(result_signals) == 1
    assert result_signals[0]["signal_title"] == "Lawsuit filed"

    # Should have 2 claim verifications (verification2 filtered because VERIFIED + no discrepancy)
    assert len(result_verifications) == 2

    # Check severity assignments
    contradicted = next(
        v for v in result_verifications if v["verification_status"] == "CONTRADICTED"
    )
    assert contradicted["severity"] == "high"

    cannot_verify = next(
        v for v in result_verifications if v["verification_status"] == "CANNOT_VERIFY"
    )
    assert cannot_verify["severity"] == "medium"

    # Check sorting (high before medium)
    assert result_verifications[0]["severity"] == "high"
    assert result_verifications[1]["severity"] == "medium"


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
        verifications=json.dumps([verification.model_dump()])
    )

    aggregator_output = ExternalSignalFindingsAggregatorOutput(
        external_signals="[]", claim_verifications="[]"
    )

    mock_callback_context.state = {
        "external_signal_findings_aggregator_output": aggregator_output,
        "external_signal_report_to_internet_output": report_to_internet_output,
    }

    await after_aggregator_callback(mock_callback_context)

    result_dict = mock_callback_context.state[
        "external_signal_findings_aggregator_output"
    ]
    result_verifications = json.loads(result_dict["claim_verifications"])

    # Should keep the verification because it has a discrepancy
    assert len(result_verifications) == 1
    assert result_verifications[0]["severity"] == "low"  # VERIFIED → low


@pytest.mark.asyncio
async def test_callback_filters_unclear_external_signals(mock_callback_context):
    """Test that external signals with reflected_in_fs='Unclear' are kept."""
    signal = ReconciledExternalSignal(
        signal_title="Unclear event",
        signal_type=["news"],
        entities_involved=["Company A"],
        event_date="2025-03-01",
        sources=json.dumps([{"url": "http://example.com", "publisher": "Reuters"}]),
        summary="Event with unclear disclosure",
        expected_fs_impact_area=["Notes"],
        expected_fs_impact_notes_expected=["Events"],
        expected_fs_impact_rationale="May be relevant",
        evidence_reflected_in_fs="Unclear",
        evidence_search_terms_used=["event"],
        evidence_not_found_statement="Ambiguous mention",
        gap_classification="NEEDS_JUDGMENT",
        severity="medium",
    )

    aggregator_output = ExternalSignalFindingsAggregatorOutput(
        external_signals=json.dumps([signal.model_dump()]), claim_verifications="[]"
    )

    mock_callback_context.state = {
        "external_signal_findings_aggregator_output": aggregator_output,
        "external_signal_report_to_internet_output": None,
    }

    await after_aggregator_callback(mock_callback_context)

    result_dict = mock_callback_context.state[
        "external_signal_findings_aggregator_output"
    ]
    result_signals = json.loads(result_dict["external_signals"])

    # Should keep signal with "Unclear" status
    assert len(result_signals) == 1
    assert result_signals[0]["evidence_reflected_in_fs"] == "Unclear"


@pytest.mark.asyncio
async def test_callback_sorting_by_severity(mock_callback_context):
    """Test that findings are correctly sorted by severity."""
    # Create signals with different severities (out of order)
    signal_low = ReconciledExternalSignal(
        signal_title="Low severity",
        signal_type=["news"],
        entities_involved=["Company A"],
        event_date="2025-01-01",
        sources=json.dumps([{"url": "http://example.com/1", "publisher": "Reuters"}]),
        summary="Minor news",
        expected_fs_impact_area=["Notes"],
        expected_fs_impact_notes_expected=["Events"],
        expected_fs_impact_rationale="Minor",
        evidence_reflected_in_fs="No",
        evidence_search_terms_used=["news"],
        evidence_not_found_statement="",
        gap_classification="NEEDS_JUDGMENT",
        severity="low",
    )

    signal_high = ReconciledExternalSignal(
        signal_title="High severity",
        signal_type=["legal_regulatory"],
        entities_involved=["Company A"],
        event_date="2025-02-01",
        sources=json.dumps([{"url": "http://example.com/2", "publisher": "Reuters"}]),
        summary="Major lawsuit",
        expected_fs_impact_area=["Notes"],
        expected_fs_impact_notes_expected=["Contingencies"],
        expected_fs_impact_rationale="Material",
        evidence_reflected_in_fs="No",
        evidence_search_terms_used=["lawsuit"],
        evidence_not_found_statement="",
        gap_classification="POTENTIAL_CONTRADICTION",
        severity="high",
    )

    signal_medium = ReconciledExternalSignal(
        signal_title="Medium severity",
        signal_type=["financing_distress"],
        entities_involved=["Company A"],
        event_date="2025-03-01",
        sources=json.dumps([{"url": "http://example.com/3", "publisher": "Reuters"}]),
        summary="Rating downgrade",
        expected_fs_impact_area=["Notes"],
        expected_fs_impact_notes_expected=["Debt"],
        expected_fs_impact_rationale="Relevant",
        evidence_reflected_in_fs="No",
        evidence_search_terms_used=["rating"],
        evidence_not_found_statement="",
        gap_classification="POTENTIAL_OMISSION",
        severity="medium",
    )

    # Add in random order
    aggregator_output = ExternalSignalFindingsAggregatorOutput(
        external_signals=json.dumps(
            [
                signal_low.model_dump(),
                signal_high.model_dump(),
                signal_medium.model_dump(),
            ]
        ),
        claim_verifications="[]",
    )

    mock_callback_context.state = {
        "external_signal_findings_aggregator_output": aggregator_output,
        "external_signal_report_to_internet_output": None,
    }

    await after_aggregator_callback(mock_callback_context)

    result_dict = mock_callback_context.state[
        "external_signal_findings_aggregator_output"
    ]
    result_signals = json.loads(result_dict["external_signals"])

    # Should be sorted: high, medium, low
    assert len(result_signals) == 3
    assert result_signals[0]["severity"] == "high"
    assert result_signals[1]["severity"] == "medium"
    assert result_signals[2]["severity"] == "low"


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
        sources=json.dumps([{"url": "http://example.com", "publisher": "Reuters"}]),
        summary="Test",
        expected_fs_impact_area=["Notes"],
        expected_fs_impact_notes_expected=["Events"],
        expected_fs_impact_rationale="Test",
        evidence_reflected_in_fs="No",
        evidence_search_terms_used=["test"],
        evidence_not_found_statement="",
        gap_classification="POTENTIAL_OMISSION",
        severity="medium",
    )

    aggregator_output = ExternalSignalFindingsAggregatorOutput(
        external_signals=json.dumps([signal.model_dump()]), claim_verifications="[]"
    )

    mock_callback_context.state = {
        "external_signal_findings_aggregator_output": aggregator_output,
        # No report_to_internet_output
    }

    await after_aggregator_callback(mock_callback_context)

    result_dict = mock_callback_context.state[
        "external_signal_findings_aggregator_output"
    ]
    result_signals = json.loads(result_dict["external_signals"])
    result_verifications = json.loads(result_dict["claim_verifications"])

    # Should have external signals but no claim verifications
    assert len(result_signals) == 1
    assert len(result_verifications) == 0


@pytest.mark.asyncio
async def test_callback_with_empty_lists(mock_callback_context):
    """Test callback with empty external signals and verifications."""
    aggregator_output = ExternalSignalFindingsAggregatorOutput(
        external_signals="[]", claim_verifications="[]"
    )

    report_to_internet_output = ExternalSignalReportToInternetOutput(verifications="[]")

    mock_callback_context.state = {
        "external_signal_findings_aggregator_output": aggregator_output,
        "external_signal_report_to_internet_output": report_to_internet_output,
    }

    await after_aggregator_callback(mock_callback_context)

    result_dict = mock_callback_context.state[
        "external_signal_findings_aggregator_output"
    ]
    result_signals = json.loads(result_dict["external_signals"])
    result_verifications = json.loads(result_dict["claim_verifications"])

    # Should have empty lists
    assert len(result_signals) == 0
    assert len(result_verifications) == 0


@pytest.mark.asyncio
async def test_callback_preserves_error_field(mock_callback_context):
    """Test that callback preserves the error field from aggregator output."""
    error_msg = "test_error: Test error message"

    aggregator_output = ExternalSignalFindingsAggregatorOutput(
        error=error_msg,
        external_signals="[]",
        claim_verifications="[]",
    )

    mock_callback_context.state = {
        "external_signal_findings_aggregator_output": aggregator_output,
    }

    await after_aggregator_callback(mock_callback_context)

    result_dict = mock_callback_context.state[
        "external_signal_findings_aggregator_output"
    ]

    # Should preserve error field
    assert result_dict["error"] is not None
    assert result_dict["error"] == error_msg


@pytest.mark.asyncio
async def test_callback_handles_report_output_without_verifications_attr(
    mock_callback_context,
):
    """Test callback handles report_to_internet output without verifications attribute."""

    class FakeOutput:
        """Mock output without verifications attribute."""

        pass

    aggregator_output = ExternalSignalFindingsAggregatorOutput(
        external_signals="[]", claim_verifications="[]"
    )

    mock_callback_context.state = {
        "external_signal_findings_aggregator_output": aggregator_output,
        "external_signal_report_to_internet_output": FakeOutput(),
    }

    # Should not raise an exception
    await after_aggregator_callback(mock_callback_context)

    result_dict = mock_callback_context.state[
        "external_signal_findings_aggregator_output"
    ]
    result_verifications = json.loads(result_dict["claim_verifications"])

    assert len(result_verifications) == 0
