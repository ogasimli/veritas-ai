"""Centralized model name configuration.

Model aliases resolve to Gemini model identifiers and can be overridden via
environment variables:

    GEMINI_PRO_MODEL   - defaults to "gemini-3-pro-preview"
    GEMINI_FLASH_MODEL - defaults to "gemini-3-flash-preview"
"""

import os

GEMINI_PRO: str = os.environ.get("GEMINI_PRO_MODEL", "gemini-3-pro-preview")
GEMINI_FLASH: str = os.environ.get("GEMINI_FLASH_MODEL", "gemini-3-flash-preview")
