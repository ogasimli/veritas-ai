"""Root pipeline agent definition and App configuration."""

from google.adk.agents import SequentialAgent
from google.adk.apps.app import App, ContextCacheConfig

from .shared.agent_selection_plugin import AgentSelectionPlugin
from .shared.debug_logging_plugin import JobAwareDebugPlugin
from .shared.document_markdown_plugin import DocumentMarkdownPlugin
from .shared.file_logging_plugin import FileLoggingPlugin
from .sub_agents import audit_orchestrator, document_validator_agent

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
        AgentSelectionPlugin(),
        DocumentMarkdownPlugin(),
        JobAwareDebugPlugin(),
        FileLoggingPlugin(),
    ],
    context_cache_config=ContextCacheConfig(
        min_tokens=2048,
        ttl_seconds=3600,
        cache_intervals=100,
    ),
)
