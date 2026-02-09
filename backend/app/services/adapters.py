"""Adapter registry for extracting findings from agent pipeline state.

Each adapter knows how to read a specific agent's output from the pipeline
state and normalize it into ``NormalizedFinding`` instances that the processor
can persist unchanged.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, ClassVar

from app.schemas.finding import NormalizedFinding


class AgentAdapter(ABC):
    """Base class for agent output adapters."""

    agent_id: ClassVar[str]
    category: ClassVar[str]
    output_keys: ClassVar[list[str]]  # State keys that indicate this agent ran
    error_keys: ClassVar[list[str]]  # State keys to check for errors
    # When True, completion is detected by output_keys appearing in state_delta
    # instead of the is_final flag on events.
    detect_via_state_delta: ClassVar[bool] = False

    @abstractmethod
    def extract_findings(
        self, agent_state: dict[str, Any]
    ) -> list[NormalizedFinding] | None:
        """Extract normalized findings from agent state.

        Returns:
            list[NormalizedFinding] if the agent ran (may be empty),
            None if the agent hasn't produced output yet.
        """
        ...

    @abstractmethod
    def extract_error(self, agent_state: dict[str, Any]) -> dict | None:
        """Extract error info from agent state, or None if no error."""
        ...

    def _check_standard_error(
        self, state: dict[str, Any], keys: list[str]
    ) -> dict | None:
        """Check for AgentError in standard output keys."""
        for key in keys:
            data = state.get(key)
            if isinstance(data, dict):
                if data.get("error") and isinstance(data["error"], dict):
                    return data["error"]
                if data.get("is_error"):
                    return data
        return None


class NumericValidationAdapter(AgentAdapter):
    """Adapter for the numeric validation aggregator.

    Reads ``numeric_validation_output`` → ``issues: list[NumericIssue]``.
    """

    agent_id: ClassVar[str] = "numeric_validation"
    category: ClassVar[str] = "numeric"
    output_keys: ClassVar[list[str]] = ["numeric_validation_output"]
    error_keys: ClassVar[list[str]] = ["numeric_validation_output"]

    def extract_findings(
        self, agent_state: dict[str, Any]
    ) -> list[NormalizedFinding] | None:
        output = agent_state.get("numeric_validation_output")
        if not isinstance(output, dict):
            return None

        issues = output.get("issues")
        if issues is None:
            return []

        findings: list[NormalizedFinding] = []
        for issue in issues:
            # TODO: compute severity by extracting materiality from the report
            # and comparing abs(difference) against it.
            severity = "medium"

            findings.append(
                NormalizedFinding(
                    description=issue.get("issue_description", ""),
                    severity=severity,
                    reasoning=(
                        f"Check type: {issue.get('check_type', '')}\n"
                        f"Formula: {issue.get('formula', '')}\n"
                        f"Difference: {issue.get('difference', '')}"
                    ),
                    source_refs=[],
                )
            )
        return findings

    def extract_error(self, agent_state: dict[str, Any]) -> dict | None:
        return self._check_standard_error(agent_state, self.error_keys)


class LogicConsistencyAdapter(AgentAdapter):
    """Adapter for the logic consistency reviewer.

    Reads ``logic_consistency_reviewer_output`` → ``findings`` list.
    """

    agent_id: ClassVar[str] = "logic_consistency"
    category: ClassVar[str] = "logic"
    output_keys: ClassVar[list[str]] = ["logic_consistency_reviewer_output"]
    error_keys: ClassVar[list[str]] = [
        "logic_consistency_detector_output",
        "logic_consistency_reviewer_output",
    ]

    def extract_findings(
        self, agent_state: dict[str, Any]
    ) -> list[NormalizedFinding] | None:
        output = agent_state.get("logic_consistency_reviewer_output")
        if not isinstance(output, dict):
            return None

        raw_findings = output.get("findings")
        if raw_findings is None:
            return []

        findings: list[NormalizedFinding] = []
        for f in raw_findings:
            findings.append(
                NormalizedFinding(
                    description=f.get("contradiction", ""),
                    severity=f.get("severity", "medium"),
                    reasoning=f"Claim: {f.get('claim', '')}\n\nReasoning: {f.get('reasoning', '')}",
                    source_refs=f.get("source_refs", []),
                )
            )
        return findings

    def extract_error(self, agent_state: dict[str, Any]) -> dict | None:
        return self._check_standard_error(agent_state, self.error_keys)


class DisclosureComplianceAdapter(AgentAdapter):
    """Adapter for the disclosure compliance reviewer.

    Reads ``disclosure_reviewer_output`` → ``findings`` list.
    """

    agent_id: ClassVar[str] = "disclosure_compliance"
    category: ClassVar[str] = "disclosure"
    output_keys: ClassVar[list[str]] = ["disclosure_reviewer_output"]
    error_keys: ClassVar[list[str]] = [
        "disclosure_scanner_output",
        "disclosure_reviewer_output",
    ]

    def extract_findings(
        self, agent_state: dict[str, Any]
    ) -> list[NormalizedFinding] | None:
        output = agent_state.get("disclosure_reviewer_output")
        if not isinstance(output, dict):
            return None

        raw_findings = output.get("findings")
        if raw_findings is None:
            return []

        findings: list[NormalizedFinding] = []
        for f in raw_findings:
            findings.append(
                NormalizedFinding(
                    description=f"{f.get('reference', '')}: {f.get('requirement', '')}",
                    severity=f.get("severity", "medium"),
                    reasoning=(
                        f"Standard: {f.get('standard')}\nID: {f.get('disclosure_id')}"
                    ),
                    source_refs=[],
                )
            )
        return findings

    def extract_error(self, agent_state: dict[str, Any]) -> dict | None:
        return self._check_standard_error(agent_state, self.error_keys)


class ExternalSignalAdapter(AgentAdapter):
    """Adapter for the external signal findings aggregator.

    Reads ``external_signal_processed_output`` — the post-processed output
    written by ``after_aggregator_callback`` (filtered, sorted, with claim
    verifications merged from report_to_internet).

    Uses ``detect_via_state_delta`` so the processor triggers on the callback
    event's state_delta rather than the LlmAgent's ``is_final`` event.
    """

    agent_id: ClassVar[str] = "external_signal"
    category: ClassVar[str] = "external"
    output_keys: ClassVar[list[str]] = ["external_signal_processed_output"]
    error_keys: ClassVar[list[str]] = [
        "external_signal_internet_to_report_output",
        "external_signal_report_to_internet_output",
        "external_signal_findings_aggregator_output",
    ]
    detect_via_state_delta: ClassVar[bool] = True

    def extract_findings(
        self, agent_state: dict[str, Any]
    ) -> list[NormalizedFinding] | None:
        output = agent_state.get("external_signal_processed_output")
        if not isinstance(output, dict):
            return None

        findings: list[NormalizedFinding] = []

        # Parse external signals (JSON string)
        signals_raw = output.get("external_signals", "[]")
        try:
            signals = (
                json.loads(signals_raw) if isinstance(signals_raw, str) else signals_raw
            )
        except (json.JSONDecodeError, TypeError):
            signals = []

        if isinstance(signals, list):
            for signal in signals:
                # Parse sources (double-nested JSON string)
                source_refs: list[str] = []
                sources_raw = signal.get("sources", "[]")
                try:
                    sources = (
                        json.loads(sources_raw)
                        if isinstance(sources_raw, str)
                        else sources_raw
                    )
                except (json.JSONDecodeError, TypeError):
                    sources = []
                if isinstance(sources, list):
                    for src in sources:
                        if isinstance(src, dict) and src.get("url"):
                            source_refs.append(src["url"])
                        elif isinstance(src, str):
                            source_refs.append(src)

                summary = signal.get("summary", "")
                not_found = signal.get("evidence_not_found_statement", "")
                reasoning_parts = [summary]
                if not_found:
                    reasoning_parts.append(not_found)

                findings.append(
                    NormalizedFinding(
                        description=signal.get("signal_title", ""),
                        severity=signal.get("severity", "medium"),
                        reasoning="\n\n".join(reasoning_parts),
                        source_refs=source_refs,
                    )
                )

        # Parse claim verifications (JSON string)
        claims_raw = output.get("claim_verifications", "[]")
        try:
            claims = (
                json.loads(claims_raw) if isinstance(claims_raw, str) else claims_raw
            )
        except (json.JSONDecodeError, TypeError):
            claims = []

        if isinstance(claims, list):
            for claim in claims:
                evidence = claim.get("evidence_summary", "")
                discrepancy = claim.get("discrepancy", "")
                reasoning_parts = []
                if evidence:
                    reasoning_parts.append(evidence)
                if discrepancy:
                    reasoning_parts.append(discrepancy)

                findings.append(
                    NormalizedFinding(
                        description=(claim.get("claim_text", "") or "")[:1].upper()
                        + (claim.get("claim_text", "") or "")[1:],
                        severity=claim.get("severity", "medium"),
                        reasoning="\n\n".join(reasoning_parts),
                        source_refs=claim.get("source_urls", []),
                    )
                )

        # If we got the output dict but no findings, return empty list (agent ran, found nothing)
        return findings

    def extract_error(self, agent_state: dict[str, Any]) -> dict | None:
        return self._check_standard_error(agent_state, self.error_keys)


ADAPTER_REGISTRY: dict[str, AgentAdapter] = {
    a.agent_id: a
    for a in [
        NumericValidationAdapter(),
        LogicConsistencyAdapter(),
        DisclosureComplianceAdapter(),
        ExternalSignalAdapter(),
    ]
}
