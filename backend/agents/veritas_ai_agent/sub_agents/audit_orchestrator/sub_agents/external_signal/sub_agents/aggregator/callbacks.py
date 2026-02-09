"""Callbacks for the aggregator agent."""

import json
import logging

from google.adk.agents.callback_context import CallbackContext

from .schema import ExternalSignalFindingsAggregatorOutput

logger = logging.getLogger(__name__)


def _extract_json_array(text: str) -> list:
    """Extract first JSON array from text that may contain trailing garbage."""
    start = text.find("[")
    if start == -1:
        return []
    try:
        result, _ = json.JSONDecoder().raw_decode(text, start)
        return result if isinstance(result, list) else []
    except json.JSONDecodeError:
        return []


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
    raw_output_key = "external_signal_findings_aggregator_output"
    processed_output_key = "external_signal_processed_output"
    aggregator_output: ExternalSignalFindingsAggregatorOutput = state.get(
        raw_output_key
    )

    if not aggregator_output:
        return

    # Parse external signals from JSON string
    try:
        if isinstance(aggregator_output, dict):
            signals_json = aggregator_output.get("external_signals")
        else:
            signals_json = aggregator_output.external_signals

        try:
            external_signals = json.loads(signals_json or "[]")
        except json.JSONDecodeError:
            logger.warning(
                "Failed direct JSON parse for external_signals, "
                "attempting extraction from: %.200s",
                signals_json,
            )
            external_signals = _extract_json_array(signals_json or "")
    except AttributeError:
        external_signals = []

    # Step 1: Pull claim verifications directly from report_to_internet output
    report_to_internet_output = state.get("external_signal_report_to_internet_output")
    claim_verifications = []

    if report_to_internet_output:
        # Parse verifications from JSON string
        if isinstance(report_to_internet_output, dict):
            verifications_str = report_to_internet_output.get("verifications", "[]")
        else:
            verifications_str = getattr(
                report_to_internet_output, "verifications", "[]"
            )
        try:
            raw_verifications = json.loads(verifications_str or "[]")
        except json.JSONDecodeError:
            logger.warning(
                "Failed direct JSON parse for verifications, "
                "attempting extraction from: %.200s",
                verifications_str,
            )
            raw_verifications = _extract_json_array(verifications_str or "")

        # Normalize if it's a dict wrapper (e.g. {"claims": [...]})
        if isinstance(raw_verifications, dict):
            raw_verifications = (
                raw_verifications.get("claims")
                or raw_verifications.get("verifications")
                or []
            )

        if not isinstance(raw_verifications, list):
            raw_verifications = []

        # Convert to ReconciledClaimVerification format (as dicts)
        for verification in raw_verifications:
            claim_verifications.append(
                {
                    "claim_text": verification.get("claim_text", ""),
                    "claim_category": verification.get("claim_category", ""),
                    "verification_status": verification.get(
                        "verification_status", "CANNOT_VERIFY"
                    ),
                    "evidence_summary": verification.get("evidence_summary", "")
                    or verification.get("verification_evidence", ""),
                    "source_urls": verification.get("source_urls", []),
                    "discrepancy": verification.get("discrepancy", ""),
                    "severity": "medium",  # Will be set below
                }
            )

    # Step 2: Assign severity to claim verifications
    severity_map = {
        "CONTRADICTED": "high",
        "CANNOT_VERIFY": "medium",
        "VERIFIED": "low",
    }

    for verification in claim_verifications:
        verification["severity"] = severity_map.get(
            verification["verification_status"], "medium"
        )

    # Step 3: Filter external signals: remove those reflected in FS
    filtered_signals = [
        signal
        for signal in external_signals
        if signal.get("evidence_reflected_in_fs") != "Yes"
    ]

    # Step 4: Filter claim verifications: remove clean verifications
    filtered_verifications = [
        verification
        for verification in claim_verifications
        if not (
            verification["verification_status"] == "VERIFIED"
            and not verification.get("discrepancy")
        )
    ]

    # Step 5: Sort by severity: high → medium → low
    severity_order = {"high": 0, "medium": 1, "low": 2}

    sorted_signals = sorted(
        filtered_signals, key=lambda x: severity_order.get(x.get("severity", "low"), 3)
    )
    sorted_verifications = sorted(
        filtered_verifications,
        key=lambda x: severity_order.get(x.get("severity", "low"), 3),
    )

    # Step 6: Update the output with both external signals and claim verifications
    existing_error = (
        aggregator_output.get("error")
        if isinstance(aggregator_output, dict)
        else getattr(aggregator_output, "error", None)
    )

    state[processed_output_key] = ExternalSignalFindingsAggregatorOutput(
        error=existing_error,
        external_signals=json.dumps(sorted_signals),
        claim_verifications=json.dumps(sorted_verifications),
    ).model_dump()
