"""Root orchestrator agent definition and App configuration."""

import os

from google.adk.agents import ParallelAgent
from google.adk.apps.app import App, ContextCacheConfig
from google.adk.plugins import DebugLoggingPlugin, LoggingPlugin

from .shared.coordination_plugin import create_coordination_plugin
from .shared.document_markdown_plugin import create_document_markdown_plugin
from .sub_agents import (
    disclosure_compliance_agent,
    external_signal_agent,
    logic_consistency_agent,
    numeric_validation_agent,
)

# Select agent mode based on environment variable (default to the main orchestrator)
agent_mode = os.environ.get("VERITAS_AGENT_MODE", "orchestrator")

if agent_mode == "numeric_validation":
    # Export numeric validation sub-agent
    root_agent = numeric_validation_agent
elif agent_mode == "logic_consistency":
    # Export logic consistency sub-agent
    root_agent = logic_consistency_agent
elif agent_mode == "disclosure_compliance":
    # Export disclosure compliance sub-agent
    root_agent = disclosure_compliance_agent
elif agent_mode == "external_signal":
    # Export external signal sub-agent
    root_agent = external_signal_agent
else:
    # Default behavior: create the main parallel orchestrator
    root_agent = ParallelAgent(
        name="AuditOrchestrator",
        description="Coordinates parallel validation agents for financial statement audit",
        sub_agents=[
            numeric_validation_agent,  # Numeric validation pipeline (adaptive batching)
            logic_consistency_agent,  # Logic consistency detection
            disclosure_compliance_agent,  # Disclosure compliance checking
            external_signal_agent,  # Bidirectional external verification with Deep Research
        ],
    )

# Define the App with the selected agent
app = App(
    name="veritas_ai_agent",
    root_agent=root_agent,
    plugins=[
        create_document_markdown_plugin(),  # Capture markdown from user message first
        create_coordination_plugin(),
        DebugLoggingPlugin(),
        LoggingPlugin(),
    ],
    context_cache_config=ContextCacheConfig(
        min_tokens=2048,
        ttl_seconds=3600,
        cache_intervals=100,  # High interval for FanOut verifiers support
    ),
)
