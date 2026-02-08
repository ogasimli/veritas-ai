"""Root pipeline agent definition and App configuration."""

import os

from google.adk.agents import SequentialAgent
from google.adk.apps.app import App, ContextCacheConfig
from google.adk.plugins import DebugLoggingPlugin, LoggingPlugin

from .shared.coordination_plugin import create_coordination_plugin
from .shared.document_markdown_plugin import create_document_markdown_plugin
from .sub_agents import (
    audit_orchestrator,
    disclosure_compliance_agent,
    document_validator_agent,
    external_signal_agent,
    logic_consistency_agent,
    numeric_validation_agent,
)

# Select agent mode based on environment variable (default to the main orchestrator)
agent_mode = os.environ.get("VERITAS_AGENT_MODE", "orchestrator")

if agent_mode == "numeric_validation":
    root_agent = numeric_validation_agent
elif agent_mode == "logic_consistency":
    root_agent = logic_consistency_agent
elif agent_mode == "disclosure_compliance":
    root_agent = disclosure_compliance_agent
elif agent_mode == "external_signal":
    root_agent = external_signal_agent
else:
    # Default: validate document type, then run parallel audit agents
    root_agent = SequentialAgent(
        name="VeritasPipeline",
        description="Validates document type then runs parallel audit agents",
        sub_agents=[
            document_validator_agent,
            audit_orchestrator,
        ],
    )

# Define the App with the selected agent
app = App(
    name="veritas_ai_agent",
    root_agent=root_agent,
    plugins=[
        create_document_markdown_plugin(),
        create_coordination_plugin(),
        DebugLoggingPlugin(),
        LoggingPlugin(),
    ],
    context_cache_config=ContextCacheConfig(
        min_tokens=2048,
        ttl_seconds=3600,
        cache_intervals=100,
    ),
)
