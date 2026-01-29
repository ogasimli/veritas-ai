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

    # Each category has 'name' and 'disclosures' fields
    categories = standards[standard_code]

    # Flatten all disclosures from all categories
    all_disclosures = []
    for category in categories:
        all_disclosures.extend(category.get("disclosures", []))

    return {"name": standard_code, "disclosures": all_disclosures}
