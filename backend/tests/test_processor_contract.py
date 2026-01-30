from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.finding import AgentResult as AgentResultModel
from app.services.processor import DocumentProcessor


@pytest.mark.asyncio
async def test_processor_extraction_contract():
    """
    Contract test to ensure DocumentProcessor correctly extracts results
    from the current session state structure produced by agents.
    """
    # 1. Setup Mock DB
    session_added = []

    db = MagicMock()
    db.get = AsyncMock()
    db.commit = AsyncMock()

    def mock_add(obj):
        if isinstance(obj, AgentResultModel):
            session_added.append(obj)

    db.add.side_effect = mock_add

    async def mock_execute(stmt):
        # Very basic simulation of select(...).where(...)
        # We just need to check if we're querying AgentResultModel
        # For simplicity in this contract test, we'll return what's been added so far
        # that matches the agent_id if possible, but honestly returning everything
        # is enough to stop the fallback from duplicating.
        results = session_added[:]
        mock_res = MagicMock()
        mock_res.scalars.return_value.all.return_value = results
        return mock_res

    db.execute = AsyncMock(side_effect=mock_execute)

    processor = DocumentProcessor(db)
    job_id = uuid4()

    # 2. Simulate Job in DB
    mock_job = MagicMock()
    mock_job.status = "processing"
    db.get.return_value = mock_job

    # 3. Define the CONTRACT: This state represents the exact keys/structure
    # expected from all sub-agents in the orchestrator.
    contract_final_state = {
        "numeric_validation": {
            "reviewer_output": {
                "findings": [
                    {
                        "fsli_name": "Cash",
                        "summary": "Numeric mismatch in Note 5",
                        "severity": "high",
                        "expected_value": 1000.0,
                        "actual_value": 950.0,
                        "discrepancy": 50.0,
                        "source_refs": ["Note 5, Page 12"],
                    }
                ]
            }
        },
        "logic_consistency": {
            "reviewer_output": {
                "findings": [
                    {
                        "fsli_name": "Revenue",
                        "claim": "Revenue increased by 10%",
                        "contradiction": "Table 1 shows a 5% decrease",
                        "severity": "high",
                        "reasoning": "Direct contradiction between MD&A and Table 1",
                        "source_refs": ["Table 1", "MD&A Section 2"],
                    }
                ]
            }
        },
        "disclosure_compliance": {
            "reviewer_output": {
                "findings": [
                    {
                        "standard": "IAS 1",
                        "disclosure_id": "IAS1-D12",
                        "requirement": "Going concern assessment",
                        "severity": "high",
                        "description": "The report fails to explicitly state the going concern assumption.",
                    }
                ]
            }
        },
        "external_signal": {
            "external_signal_findings": {
                "findings": [
                    {
                        "finding_type": "external_signal",
                        "summary": "Major lawsuit filed against company",
                        "severity": "medium",
                        "source_urls": ["https://reuters.com/news/123"],
                        "category": "litigation",
                        "details": "Publication date: 2025-06-15\nPotential contradiction: Contradicts 'No pending litigation' claim",
                    },
                    {
                        "finding_type": "claim_contradiction",
                        "summary": "CONTRADICTED: Headquartered in London",
                        "severity": "high",
                        "source_urls": ["https://company-registry.gov/uk"],
                        "category": "claim_verification",
                        "details": "Claim: Headquartered in London\nStatus: CONTRADICTED\nEvidence: Registry shows HQ moved to Paris in 2024\nDiscrepancy: Location mismatch",
                    },
                ]
            }
        },
    }

    # 4. Mock the runner to yield this state
    with (
        patch("app.services.processor.InMemoryRunner") as MockRunner,
        patch("app.services.processor.get_settings") as mock_get_settings,
    ):
        mock_get_settings.return_value = MagicMock(use_dummy_agents=False)
        mock_runner_instance = MockRunner.return_value
        mock_runner_instance.session_service.create_session = AsyncMock(
            return_value=MagicMock(id="test-session", user_id="test-user")
        )
        mock_runner_instance.session_service.get_session = AsyncMock(
            return_value=MagicMock(state=contract_final_state)
        )

        async def mock_run_async(*args, **kwargs):
            event = MagicMock()
            event.session.state = contract_final_state
            event.actions = MagicMock()
            event.actions.state_delta = contract_final_state
            event.is_final_response.return_value = True
            yield event

        mock_runner_instance.run_async = mock_run_async

        # 5. Execute processing
        await processor.process_document(job_id=job_id, extracted_text="Dummy text")

    # 6. Verify Contract Adherence
    added_results = session_added
    categories = [f.category for f in added_results]

    assert "numeric" in categories
    assert "logic" in categories
    assert "disclosure" in categories
    assert "external" in categories

    # We expect EXACTLY 5 results. If fallback logic is buggy, we'd get 10.
    assert len(added_results) == 5, (
        f"Expected 5 results, got {len(added_results)}. Check for duplicates!"
    )

    print("\n✅ Processor Contract Test Passed!")


@pytest.mark.asyncio
async def test_processor_empty_findings_contract():
    """
    Contract test to ensure DocumentProcessor correctly handles empty findings
    and saves the expected default values (None for description/severity, {} for raw_data).
    """
    # 1. Setup Mock DB
    session_added = []

    db = MagicMock()
    db.get = AsyncMock()
    db.commit = AsyncMock()

    def mock_add(obj):
        if isinstance(obj, AgentResultModel):
            session_added.append(obj)

    db.add.side_effect = mock_add

    async def mock_execute(stmt):
        results = session_added[:]
        mock_res = MagicMock()
        mock_res.scalars.return_value.all.return_value = results
        return mock_res

    db.execute = AsyncMock(side_effect=mock_execute)

    processor = DocumentProcessor(db)
    job_id = uuid4()

    # 2. Simulate Job in DB
    mock_job = MagicMock()
    mock_job.status = "processing"
    db.get.return_value = mock_job

    # 3. Define State with EMPTY findings
    contract_empty_state = {
        "numeric_validation": {"reviewer_output": {"findings": []}},
        "logic_consistency": {"reviewer_output": {"findings": []}},
        "disclosure_compliance": {"reviewer_output": {"findings": []}},
        "external_signal": {
            "external_signal_findings": {"findings": []},
        },
    }

    # 4. Mock the runner
    with (
        patch("app.services.processor.InMemoryRunner") as MockRunner,
        patch("app.services.processor.get_settings") as mock_get_settings,
    ):
        mock_get_settings.return_value = MagicMock(use_dummy_agents=False)
        mock_runner_instance = MockRunner.return_value

        mock_session = MagicMock()
        mock_session.id = "test-session-empty"
        mock_session.user_id = "test-user"
        mock_session.state = contract_empty_state

        mock_runner_instance.session_service.create_session = AsyncMock(
            return_value=mock_session
        )
        mock_runner_instance.session_service.get_session = AsyncMock(
            return_value=mock_session
        )

        mock_runner_instance.app_name = "test-app"

        async def mock_run_async(*args, **kwargs):
            event = MagicMock()
            event.is_final_response.return_value = True
            event.actions = MagicMock()
            event.actions.state_delta = contract_empty_state
            yield event

        mock_runner_instance.run_async = mock_run_async

        # 5. Execute processing
        try:
            await processor.process_document(job_id=job_id, extracted_text="Dummy text")
        except Exception as e:
            pytest.fail(f"Processor failed with error: {e}")

    # 6. Verify Database Inserts
    added_results = session_added

    # We expect 4 results (numeric, logic, disclosure, external)
    assert len(added_results) == 4, f"Expected 4 results, got {len(added_results)}"

    categories_found = {r.category for r in added_results}
    assert "numeric" in categories_found
    assert "logic" in categories_found

    for result in added_results:
        assert result.description is None, (
            f"Description should be None for {result.category}"
        )
        assert result.severity is None
        assert result.raw_data == {}
        assert result.error is None

    print("\n✅ Processor Empty Findings Contract Test Passed!")
