from google.adk.agents import SequentialAgent

from .extractor.agent import extractor_agent
from .reviewer.agent import reviewer_agent
from .verifier.agent import verifier_agent

legacy_pipeline = SequentialAgent(
    name="LegacyNumericValidationPipeline",
    description="Legacy FSLI-based numeric validation pipeline.",
    sub_agents=[
        extractor_agent,
        verifier_agent,
        reviewer_agent,
    ],
)
