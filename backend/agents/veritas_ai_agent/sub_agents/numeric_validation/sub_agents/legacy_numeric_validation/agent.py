from google.adk.agents import SequentialAgent

from .extractor.agent import fsli_extractor_agent
from .reviewer.agent import reviewer_agent
from .verifier.agent import verifier_agent

legacy_pipeline = SequentialAgent(
    name="LegacyNumericValidation",
    description="Legacy FSLI-based numeric validation pipeline.",
    sub_agents=[
        fsli_extractor_agent,
        verifier_agent,
        reviewer_agent,
    ],
)
