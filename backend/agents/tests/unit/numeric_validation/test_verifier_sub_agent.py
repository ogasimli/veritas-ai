"""Tests for FanOutVerifierAgent."""

import dotenv
import pytest

from veritas_ai_agent.sub_agents.numeric_validation.sub_agents.verifier import (
    CheckType,
    FanOutVerifierAgent,
    VerificationCheck,
    VerifierAgentOutput,
    create_verifier_agent,
    verifier_agent,
)

pytest_plugins = ("pytest_asyncio",)


@pytest.fixture(scope="session", autouse=True)
def load_env():
    dotenv.load_dotenv()


def test_fan_out_verifier_agent_structure():
    """Verify FanOutVerifierAgent is a CustomAgent."""
    assert verifier_agent.name == "FanOutVerifierAgent"
    assert isinstance(verifier_agent, FanOutVerifierAgent)


def test_create_verifier_agent():
    """Verify verifier factory creates valid agents."""
    agent = create_verifier_agent(
        name="test_verifier", fsli_name="Revenue", output_key="checks:Revenue"
    )
    assert agent.name == "test_verifier"
    assert agent.model == "gemini-3-pro-preview"
    assert agent.code_executor is not None


def test_verification_check_schema():
    """Verify VerificationCheck schema."""
    check = VerificationCheck(
        fsli_name="Revenue",
        check_type=CheckType.IN_TABLE_SUM,
        description="Product + Service = Total Revenue",
        expected_value=1500000.0,
        actual_value=1500000.0,
        check_passed=True,
        source_refs=["Table 4, Row 12"],
        code_executed="1000000 + 500000 == 1500000",
    )
    assert check.check_passed is True


def test_verifier_agent_output_schema():
    """Verify VerifierAgentOutput schema."""
    output = VerifierAgentOutput(checks=[])
    assert output.checks == []
