from google.adk.runners import InMemoryRunner
from google.genai import Client
from app.config import get_settings

async def get_adk_runner() -> InMemoryRunner:
    """
    Initialize and return a configured ADK InMemoryRunner.
    Uses the Google API key from settings.
    """
    settings = get_settings()
    
    if not settings.google_api_key:
        raise ValueError("GOOGLE_API_KEY is not set in environment or .env file")
        
    client = Client(api_key=settings.google_api_key, http_options={'api_version': 'v1alpha'})
    runner = InMemoryRunner(client=client)
    return runner
