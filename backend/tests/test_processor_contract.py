import json
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

    State shapes match the ACTUAL agent output schemas:
    - numeric_validation_output (AggregatorOutput with NumericIssue items)
    - logic_consistency_reviewer_output (findings list)
    - disclosure_reviewer_output (findings list)
    - external_signal_findings_aggregator_output (JSON string fields)
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

    # 3. Define the CONTRACT: matches CURRENT agent output schemas
    contract_final_state = {
        "numeric_validation": {
            "numeric_validation_output": {
                "issues": [
                    {
                        "issue_description": "Gross Profit does not equal Revenue minus COGS",
                        "check_type": "in_table",
                        "formula": "5000 - 2000 = 3000 != 3500",
                        "difference": 500.0,
                    },
                    {
                        "issue_description": "MD&A claims 500% growth but actual is 400%",
                        "check_type": "cross_table",
                        "formula": "(5000 - 1000) / 1000 = 4.0 != 5.0",
                        "difference": 100.0,
                    },
                ]
            },
        },
        "logic_consistency": {
            "logic_consistency_reviewer_output": {
                "findings": [
                    {
                        "fsli_name": "Revenue / Operating Expenses",
                        "claim": "Revenue increased by 500%",
                        "contradiction": "Implausible to 5x revenue while closing all facilities",
                        "severity": "high",
                        "reasoning": "Per-employee output would need to jump 33x",
                        "source_refs": ["Income Statement", "MD&A Paragraph 1"],
                    }
                ]
            }
        },
        "disclosure_compliance": {
            "disclosure_reviewer_output": {
                "findings": [
                    {
                        "standard": "IAS 19",
                        "disclosure_id": "IAS19-D1",
                        "reference": "IFRS15p126(l)",
                        "severity": "high",
                        "requirement": "Disclosure of employee benefits expense",
                    }
                ]
            }
        },
        "external_signal": {
            "external_signal_processed_output": {
                "external_signals": json.dumps(
                    [
                        {
                            "signal_title": "S&P downgraded company to Selective Default",
                            "signal_type": ["financing_distress"],
                            "entities_involved": ["Veritas Technologies"],
                            "event_date": "2024-11-15",
                            "sources": json.dumps(
                                [
                                    {
                                        "url": "https://spglobal.com/ratings",
                                        "publisher": "S&P Global",
                                    }
                                ]
                            ),
                            "summary": "S&P downgraded Veritas to SD after distressed debt exchange.",
                            "expected_fs_impact_area": ["Notes"],
                            "expected_fs_impact_notes_expected": ["Subsequent events"],
                            "expected_fs_impact_rationale": "Material credit event requires disclosure.",
                            "evidence_reflected_in_fs": "No",
                            "evidence_search_terms_used": ["downgrade", "S&P"],
                            "evidence_not_found_statement": "No mention of credit downgrade.",
                            "gap_classification": "POTENTIAL_OMISSION",
                            "severity": "high",
                        }
                    ]
                ),
                "claim_verifications": json.dumps(
                    [
                        {
                            "claim_text": "Company closed Seattle facility",
                            "claim_category": "operational",
                            "verification_status": "CONTRADICTED",
                            "evidence_summary": "No public records confirm this facility exists.",
                            "source_urls": ["https://example.com/records"],
                            "discrepancy": "Facility cannot be verified",
                            "severity": "high",
                        }
                    ]
                ),
                "error": None,
            }
        },
        # Top-level key for state_delta detection (callback writes here)
        "external_signal_processed_output": {
            "external_signals": json.dumps(
                [
                    {
                        "signal_title": "S&P downgraded company to Selective Default",
                        "signal_type": ["financing_distress"],
                        "entities_involved": ["Veritas Technologies"],
                        "event_date": "2024-11-15",
                        "sources": json.dumps(
                            [
                                {
                                    "url": "https://spglobal.com/ratings",
                                    "publisher": "S&P Global",
                                }
                            ]
                        ),
                        "summary": "S&P downgraded Veritas to SD after distressed debt exchange.",
                        "expected_fs_impact_area": ["Notes"],
                        "expected_fs_impact_notes_expected": ["Subsequent events"],
                        "expected_fs_impact_rationale": "Material credit event requires disclosure.",
                        "evidence_reflected_in_fs": "No",
                        "evidence_search_terms_used": ["downgrade", "S&P"],
                        "evidence_not_found_statement": "No mention of credit downgrade.",
                        "gap_classification": "POTENTIAL_OMISSION",
                        "severity": "high",
                    }
                ]
            ),
            "claim_verifications": json.dumps(
                [
                    {
                        "claim_text": "Company closed Seattle facility",
                        "claim_category": "operational",
                        "verification_status": "CONTRADICTED",
                        "evidence_summary": "No public records confirm this facility exists.",
                        "source_urls": ["https://example.com/records"],
                        "discrepancy": "Facility cannot be verified",
                        "severity": "high",
                    }
                ]
            ),
            "error": None,
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

    # 2 numeric + 1 logic + 1 disclosure + 2 external (1 signal + 1 claim) = 6
    assert len(added_results) == 6, (
        f"Expected 6 results, got {len(added_results)}. Check for duplicates!"
    )

    # Verify numeric findings use NormalizedFinding fields
    numeric_results = [r for r in added_results if r.category == "numeric"]
    assert len(numeric_results) == 2
    for r in numeric_results:
        assert r.description is not None
        assert r.severity is not None
        assert r.reasoning is not None
        assert (
            "check_type" in (r.reasoning or "").lower()
            or "formula" in (r.reasoning or "").lower()
        )

    # Verify external signal findings parsed from JSON strings
    external_results = [r for r in added_results if r.category == "external"]
    assert len(external_results) == 2
    # One should be signal, one claim verification
    descriptions = [r.description for r in external_results]
    assert any("S&P" in d for d in descriptions), "External signal not parsed"
    assert any("CONTRADICTED" in d for d in descriptions), (
        "Claim verification not parsed"
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

    # 3. Define State with EMPTY findings (matches current schemas)
    contract_empty_state = {
        "numeric_validation": {
            "numeric_validation_output": {"issues": []},
        },
        "logic_consistency": {"logic_consistency_reviewer_output": {"findings": []}},
        "disclosure_compliance": {"disclosure_reviewer_output": {"findings": []}},
        "external_signal": {
            "external_signal_processed_output": {
                "external_signals": "[]",
                "claim_verifications": "[]",
                "error": None,
            },
        },
        # Top-level key for state_delta detection
        "external_signal_processed_output": {
            "external_signals": "[]",
            "claim_verifications": "[]",
            "error": None,
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
