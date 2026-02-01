"""Tool for loading IFRS disclosure checklists."""

from pathlib import Path
from typing import Any

import yaml

CHECKLIST_PATH = (
    Path(__file__).parent.parent.parent.parent
    / "data"
    / "ifrs_disclosure_checklist.yaml"
)

# Module-level cache for checklist data
_CHECKLIST_CACHE: dict[str, Any] | None = None


def _normalize_code(code: str) -> str:
    """Normalize standard code for comparison (uppercase, no whitespace)."""
    return "".join(code.upper().split())


def load_standard_checklist(standard_code: str) -> dict[str, Any]:
    """Load disclosure checklist for a specific IFRS/IAS standard.

    Args:
        standard_code: Standard identifier (e.g., "IAS 1", "IFRS 15")

    Returns:
        Dictionary with standard name and flattened list of disclosure requirements
        from all categories

    Example:
        {
            "name": "Revenue from Contracts with Customers",
            "disclosures": [
                {
                    "id": "A1.1.1",
                    "reference": "1p15, 1p27",
                    "requirement": "Financial statements present fairly..."
                }
            ]
        }

    Raises:
        ValueError: If standard code is not found in checklist
        FileNotFoundError: If checklist file doesn't exist
    """
    global _CHECKLIST_CACHE
    if _CHECKLIST_CACHE is None:
        if not CHECKLIST_PATH.exists():
            raise FileNotFoundError(f"Checklist file not found at {CHECKLIST_PATH}")

        with open(CHECKLIST_PATH) as f:
            data = yaml.safe_load(f) or {}
            _CHECKLIST_CACHE = data.get("standards") or {}

    standards = _CHECKLIST_CACHE

    # try exact match first
    if standard_code in standards:
        target_key = standard_code
    else:
        # short-circuiting search with normalization
        normalized_input = _normalize_code(standard_code)
        target_key = None
        for k in standards.keys():
            if _normalize_code(k) == normalized_input:
                target_key = k
                break

        if not target_key:
            available = list(standards.keys())
            raise ValueError(
                f"Standard '{standard_code}' not found in checklist. "
                f"Available standards: {', '.join(sorted(available))}"
            )

    # Each category has 'name' and 'disclosures' fields
    categories = standards.get(target_key) or []

    # Flatten all disclosures from all categories
    all_disclosures = []
    for category in categories:
        if isinstance(category, dict):
            all_disclosures.extend(category.get("disclosures", []) or [])

    return {"name": target_key, "disclosures": all_disclosures}
