"""Callbacks for the aggregator agent."""

from google.adk.agents.callback_context import CallbackContext

from .schema import (
    ExternalSignalFindingsAggregatorOutput,
    ReconciledClaimVerification,
)


async def after_aggregator_callback(callback_context: CallbackContext) -> None:
    """
    Post-process aggregator output to:
    1. Pull claim verifications from report_to_internet output (bypassing LLM)
    2. Assign severity to claim verifications based on verification_status
    3. Filter verified items
    4. Sort findings by severity
    5. Combine into final output

    Severity mapping for claim verifications:
    - CONTRADICTED → high
    - CANNOT_VERIFY → medium
    - VERIFIED → low

    Filtering rules:
    - Remove external signals where reflected_in_fs = "Yes" (already disclosed)
    - Remove claim verifications where status = "VERIFIED" AND no discrepancies

    Sorting rules:
    - Sort both lists by severity: high → medium → low
    """
    state = callback_context.state
    output_key = "external_signal_findings_aggregator_output"
    aggregator_output: ExternalSignalFindingsAggregatorOutput = state.get(output_key)

    if not aggregator_output:
        return

    # Step 1: Pull claim verifications directly from report_to_internet output
    report_to_internet_output = state.get("external_signal_report_to_internet_output")
    claim_verifications = []

    if report_to_internet_output and hasattr(
        report_to_internet_output, "verifications"
    ):
        # Convert ExternalSignalClaimVerification to ReconciledClaimVerification
        for verification in report_to_internet_output.verifications:
            claim_verifications.append(
                ReconciledClaimVerification(
                    claim_text=verification.claim_text,
                    claim_category=verification.claim_category,
                    verification_status=verification.verification_status,
                    evidence_summary=verification.evidence_summary,
                    source_urls=verification.source_urls,
                    discrepancy=verification.discrepancy,
                    severity="medium",  # Will be set below
                )
            )

    # Step 2: Assign severity to claim verifications
    severity_map = {
        "CONTRADICTED": "high",
        "CANNOT_VERIFY": "medium",
        "VERIFIED": "low",
    }

    for verification in claim_verifications:
        verification.severity = severity_map.get(
            verification.verification_status, "medium"
        )

    # Step 3: Filter external signals: remove those reflected in FS
    filtered_signals = [
        signal
        for signal in aggregator_output.external_signals
        if signal.evidence_in_fs.reflected_in_fs != "Yes"
    ]

    # Step 4: Filter claim verifications: remove clean verifications
    filtered_verifications = [
        verification
        for verification in claim_verifications
        if not (
            verification.verification_status == "VERIFIED"
            and not verification.discrepancy
        )
    ]

    # Step 5: Sort by severity: high → medium → low
    severity_order = {"high": 0, "medium": 1, "low": 2}

    sorted_signals = sorted(
        filtered_signals, key=lambda x: severity_order.get(x.severity, 3)
    )
    sorted_verifications = sorted(
        filtered_verifications, key=lambda x: severity_order.get(x.severity, 3)
    )

    # Step 6: Update the output with both external signals and claim verifications
    state[output_key] = ExternalSignalFindingsAggregatorOutput(
        error=aggregator_output.error,
        external_signals=sorted_signals,
        claim_verifications=sorted_verifications,
    )
