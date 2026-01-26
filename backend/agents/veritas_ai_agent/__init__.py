import os

import dotenv

dotenv.load_dotenv()

# Select agent mode based on environment variable (default to the main orchestrator)
agent_mode = os.environ.get("VERITAS_AGENT_MODE", "orchestrator")

if agent_mode == "numeric_validation":
    from .sub_agents.numeric_validation import root_agent
elif agent_mode == "logic_consistency":
    from .sub_agents.logic_consistency import root_agent
elif agent_mode == "disclosure_compliance":
    from .sub_agents.disclosure_compliance import root_agent
elif agent_mode == "external_signal":
    from .sub_agents.external_signal import root_agent
else:
    # Default behavior: export the main parallel orchestrator
    from .agent import root_agent

__all__ = ["root_agent"]
