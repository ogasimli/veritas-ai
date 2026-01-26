"""Tool for loading IFRS disclosure checklists."""

from pathlib import Path
from typing import Any

import yaml

CHECKLIST_PATH = (
    Path(__file__).parent.parent.parent.parent
    / "data"
    / "ifrs_disclosure_checklist.yaml"
)


def load_standard_checklist(standard_code: str) -> dict[str, Any]:
    """Load disclosure checklist for a specific IFRS/IAS standard.

    Args:
        standard_code: Standard identifier (e.g., "IAS 1", "IFRS 15")

    Returns:
        Dictionary with standard name and list of disclosure requirements

    Example:
        {
            "name": "Revenue from Contracts with Customers",
            "disclosures": [
                {
                    "id": "IFRS15-D1",
                    "requirement": "Contract balances",
                    "description": "Opening and closing balances..."
                }
            ]
        }

    Raises:
        ValueError: If standard code is not found in checklist
        FileNotFoundError: If checklist file doesn't exist
    """
    if not CHECKLIST_PATH.exists():
        raise FileNotFoundError(f"Checklist file not found at {CHECKLIST_PATH}")

    with open(CHECKLIST_PATH) as f:
        data = yaml.safe_load(f)

    standards = data.get("standards", {})
    if standard_code not in standards:
        available = list(standards.keys())
        raise ValueError(
            f"Standard '{standard_code}' not found in checklist. "
            f"Available standards: {', '.join(sorted(available))}"
        )

    return standards[standard_code]


def get_all_standards() -> list[str]:
    """Get list of all available standard codes.

    Returns:
        List of standard codes (e.g., ['IAS 1', 'IFRS 15', ...])

    Raises:
        FileNotFoundError: If checklist file doesn't exist
    """
    if not CHECKLIST_PATH.exists():
        raise FileNotFoundError(f"Checklist file not found at {CHECKLIST_PATH}")

    with open(CHECKLIST_PATH) as f:
        data = yaml.safe_load(f)

    return list(data.get("standards", {}).keys())


def get_disclosure_count(standard_code: str) -> int:
    """Get count of disclosures for a standard.

    Args:
        standard_code: Standard identifier (e.g., "IAS 1")

    Returns:
        Number of disclosure requirements for the standard

    Raises:
        ValueError: If standard code is not found
    """
    checklist = load_standard_checklist(standard_code)
    return len(checklist.get("disclosures", []))
