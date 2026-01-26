from google.genai import types


def get_default_retry_config() -> types.HttpRetryOptions:
    """Standard retry options for all agents."""
    return types.HttpRetryOptions(
        initial_delay=1,  # seconds
        max_delay=10,  # seconds
        attempts=3,
    )
