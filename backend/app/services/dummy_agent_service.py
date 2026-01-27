"""Dummy agent service for frontend testing without inference costs."""

import asyncio
from datetime import datetime
from uuid import UUID

from app.services.websocket_manager import manager


class DummyAgentService:
    """Simulates agent responses for frontend testing."""

    def __init__(self):
        """Initialize dummy agent configurations."""
        self.agent_configs = [
            {
                "agent_id": "numeric_validation",
                "delay": 2.5,
                "response_type": "success",
                "findings": [
                    {
                        "summary": "Discrepancy in total revenue calculation",
                        "severity": "high",
                        "expected_value": "1,250,000",
                        "actual_value": "1,248,500",
                        "discrepancy": "1,500",
                        "source_refs": [
                            {"text": "Page 12, Revenue Table", "location": "p12"},
                            {"text": "Note 3: Revenue Recognition", "location": "p8"},
                        ],
                    },
                    {
                        "summary": "Asset depreciation mismatch",
                        "severity": "medium",
                        "expected_value": "45,000",
                        "actual_value": "43,200",
                        "discrepancy": "1,800",
                        "source_refs": [
                            {
                                "text": "Page 15, Fixed Assets Schedule",
                                "location": "p15",
                            }
                        ],
                    },
                ],
            },
            {
                "agent_id": "logic_consistency",
                "delay": 3.5,
                "response_type": "success",
                "findings": [
                    {
                        "contradiction": "Inconsistent liability reporting",
                        "severity": "high",
                        "claim": "Total liabilities stated as $500,000 in summary but detailed breakdown sums to $485,000",
                        "reasoning": "The summary figure does not match the sum of individual liability items listed in Note 7",
                        "source_refs": [
                            {"text": "Page 10, Financial Summary", "location": "p10"},
                            {"text": "Page 18, Note 7: Liabilities", "location": "p18"},
                        ],
                    },
                ],
            },
            {
                "agent_id": "disclosure_compliance",
                "delay": 4.2,
                "response_type": "empty",
                "findings": [],
            },
            {
                "agent_id": "external_signal",
                "delay": 5.0,
                "response_type": "error",
                "error": {
                    "agent_name": "external_signal",
                    "error_type": "ConnectionError",
                    "error_message": "Failed to connect to external data source: API rate limit exceeded",
                },
            },
        ]

    async def run_dummy_agents(self, job_id: UUID):
        """
        Simulate agent execution with realistic delays and responses.
        Yields results as they complete.

        Args:
            job_id: The job UUID

        Yields:
             Tuple of (agent_id, findings, error)
        """
        print(f"\n{'=' * 80}", flush=True)
        print("🎭 DUMMY AGENT MODE ACTIVE", flush=True)
        print("   Using simulated responses for frontend testing", flush=True)
        print(f"   Job ID: {job_id}", flush=True)
        print(f"{'=' * 80}\n", flush=True)

        # Create tasks for all agents
        tasks = [self._simulate_agent(job_id, config) for config in self.agent_configs]

        # Yield results as they complete
        for future in asyncio.as_completed(tasks):
            result = await future
            yield result

        print(f"\n{'=' * 80}", flush=True)
        print("🎭 DUMMY AGENT PIPELINE COMPLETED", flush=True)
        print(f"   Total agents: {len(self.agent_configs)}", flush=True)
        print(
            f"   Successful: {sum(1 for c in self.agent_configs if c['response_type'] == 'success')}"
        )
        print(
            f"   Empty: {sum(1 for c in self.agent_configs if c['response_type'] == 'empty')}"
        )
        print(
            f"   Errors: {sum(1 for c in self.agent_configs if c['response_type'] == 'error')}"
        )
        print(f"{'=' * 80}\n", flush=True)

    async def _simulate_agent(
        self, job_id: UUID, config: dict
    ) -> tuple[str, list, dict | None]:
        """
        Simulate a single agent execution.

        Args:
            job_id: The job UUID
            config: Agent configuration dict

        Returns:
            Tuple of (agent_id, findings, error)
        """
        agent_id = config["agent_id"]
        delay = config["delay"]
        response_type = config["response_type"]

        # Send agent_started message
        await manager.send_to_audit(
            str(job_id),
            {
                "type": "agent_started",
                "agent_id": agent_id,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
        print(f"   🎯 Agent '{agent_id}' STARTED (dummy)", flush=True)

        # Simulate processing delay
        await asyncio.sleep(delay)

        # Handle different response types
        if response_type == "success":
            findings = config["findings"]

            # Send completion message
            await manager.send_to_audit(
                str(job_id),
                {
                    "type": "agent_completed",
                    "agent_id": agent_id,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
            print(
                f"   ✅ Agent '{agent_id}' COMPLETED with {len(findings)} findings (dummy)",
                flush=True,
            )
            return agent_id, findings, None

        elif response_type == "empty":
            # Send completion with no findings
            await manager.send_to_audit(
                str(job_id),
                {
                    "type": "agent_completed",
                    "agent_id": agent_id,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
            print(
                f"   ✅ Agent '{agent_id}' COMPLETED with 0 findings (dummy)",
                flush=True,
            )
            return agent_id, [], None

        elif response_type == "error":
            error_data = config["error"]

            # Send completion message (same as success/empty)
            await manager.send_to_audit(
                str(job_id),
                {
                    "type": "agent_completed",
                    "agent_id": agent_id,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
            print(
                f"   ❌ Agent '{agent_id}' FAILED: {error_data['error_message']} (dummy)",
                flush=True,
            )
            return agent_id, [], error_data

        return agent_id, [], None
