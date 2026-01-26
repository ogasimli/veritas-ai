from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.finding import Finding as FindingModel
from app.services.processor import DocumentProcessor


@pytest.mark.asyncio
async def test_processor_extraction_contract():
    """
    Contract test to ensure DocumentProcessor correctly extracts findings
    from the current session state structure produced by agents.
    """
    # 1. Setup Mock DB
    db = MagicMock()
    db.get = AsyncMock()
    db.commit = AsyncMock()
    db.add = MagicMock()
    db.execute = AsyncMock(
        return_value=MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        )
    )

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
            "internet_to_report_findings": {
                "findings": [
                    {
                        "signal_type": "news",
                        "summary": "Major lawsuit filed against company",
                        "source_url": "https://reuters.com/news/123",
                        "publication_date": "2025-06-15",
                        "potential_contradiction": "Contradicts 'No pending litigation' claim",
                    }
                ]
            },
            "report_to_internet_findings": {
                "verifications": [
                    {
                        "claim": "Headquartered in London",
                        "status": "CONTRADICTED",
                        "evidence_summary": "Registry shows HQ moved to Paris in 2024",
                        "source_urls": ["https://company-registry.gov/uk"],
                        "discrepancy": "Location mismatch",
                    }
                ]
            },
        },
    }

    # 4. Mock the runner to yield this state
    with patch("app.services.processor.InMemoryRunner") as MockRunner:
        mock_runner_instance = MockRunner.return_value
        mock_runner_instance.session_service.create_session = AsyncMock(
            return_value=MagicMock(id="test-session", user_id="test-user")
        )
        mock_runner_instance.session_service.get_session = AsyncMock(
            return_value=MagicMock(state=contract_final_state)
        )

        # Mock run_async to yield an event with our contract state
        async def mock_run_async(*args, **kwargs):
            event = MagicMock()
            event.session.state = contract_final_state
            yield event

        mock_runner_instance.run_async = mock_run_async

        # 5. Execute processing
        await processor.process_document(job_id=job_id, extracted_text="Dummy text")

    # 6. Verify Contract Adherence (Database Inserts)
    # Check if all 5 findings (from 4 categories) were added to the DB
    added_findings = [
        args[0]
        for args, _ in db.add.call_args_list
        if isinstance(args[0], FindingModel)
    ]

    categories = [f.category for f in added_findings]
    assert "numeric" in categories
    assert "logic" in categories
    assert "disclosure" in categories
    assert (
        "external" in categories
    )  # Both internet->report and report->internet are 'external'

    assert len(added_findings) == 5  # 1 numeric, 1 logic, 1 disclosure, 2 external

    print("\n✅ Processor Contract Test Passed!")
