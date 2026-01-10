import os
from google.adk.runners import InMemoryRunner
from app.config import get_settings

async def get_adk_runner(agent=None, app_name: str = "veritas-ai") -> InMemoryRunner:
    """
    Initialize and return a configured ADK InMemoryRunner.
    Uses the Google API key from settings.

    Args:
        agent: Optional agent to bind to the runner
        app_name: Name of the application
    """
    settings = get_settings()

    if not settings.google_api_key:
        raise ValueError("GOOGLE_API_KEY is not set in environment or .env file")

    # Set API key in environment for google-genai to use
    os.environ['GOOGLE_API_KEY'] = settings.google_api_key

    # InMemoryRunner will use the API key from environment
    if agent:
        runner = InMemoryRunner(agent=agent, app_name=app_name)
    else:
        runner = InMemoryRunner(app_name=app_name)
    return runner
