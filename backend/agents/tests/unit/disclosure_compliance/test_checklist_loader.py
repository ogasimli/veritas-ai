from unittest.mock import mock_open, patch

import pytest

from veritas_ai_agent.sub_agents.disclosure_compliance.tools.checklist_loader import (
    _normalize_code,
    load_standard_checklist,
)


def test_normalize_code():
    assert _normalize_code("IAS 1") == "IAS1"
    assert _normalize_code("ias 1") == "IAS1"
    assert _normalize_code(" IFRS 13 ") == "IFRS13"
    assert (
        _normalize_code("IFRS-13") == "IFRS-13"
    )  # Current implementation only replaces spaces


@patch(
    "veritas_ai_agent.sub_agents.disclosure_compliance.tools.checklist_loader.CHECKLIST_PATH"
)
@patch(
    "builtins.open",
    new_callable=mock_open,
    read_data="standards:\n  IAS 1:\n  - name: Cat1\n    disclosures:\n    - id: 1\n  IFRS 6:\n  - name: Cat2\n    disclosures:\n    - id: 2",
)
def test_load_standard_checklist_exact(mock_file, mock_path):
    from veritas_ai_agent.sub_agents.disclosure_compliance.tools import checklist_loader

    checklist_loader._CHECKLIST_CACHE = None
    mock_path.exists.return_value = True
    result = load_standard_checklist("IAS 1")
    assert result["name"] == "IAS 1"
    assert len(result["disclosures"]) == 1


@patch(
    "veritas_ai_agent.sub_agents.disclosure_compliance.tools.checklist_loader.CHECKLIST_PATH"
)
@patch(
    "builtins.open",
    new_callable=mock_open,
    read_data="""
standards:
  IAS 1:
  - name: Cat1
    disclosures:
    - id: IAS1-ID
  IFRS 6:
  - name: Cat2
    disclosures:
    - id: IFRS6-ID
""",
)
def test_load_standard_checklist_normalized(mock_file, mock_path):
    from veritas_ai_agent.sub_agents.disclosure_compliance.tools import checklist_loader

    checklist_loader._CHECKLIST_CACHE = None
    mock_path.exists.return_value = True

    # Case insensitive -> should return IAS 1 content
    res1 = load_standard_checklist("ias 1")
    assert res1["name"] == "IAS 1"
    assert res1["disclosures"][0]["id"] == "IAS1-ID"

    # No space -> should return IFRS 6 content
    res2 = load_standard_checklist("IFRS6")
    assert res2["name"] == "IFRS 6"
    assert res2["disclosures"][0]["id"] == "IFRS6-ID"

    # Mixed and spaces -> should return IFRS 6 content
    res3 = load_standard_checklist(" ifrs 6 ")
    assert res3["name"] == "IFRS 6"
    assert res3["disclosures"][0]["id"] == "IFRS6-ID"


@patch(
    "veritas_ai_agent.sub_agents.disclosure_compliance.tools.checklist_loader.CHECKLIST_PATH"
)
@patch(
    "builtins.open",
    new_callable=mock_open,
    read_data="standards:\n  IAS 1:\n  - name: Cat1\n    disclosures:\n    - id: 1",
)
def test_load_standard_checklist_not_found(mock_file, mock_path):
    from veritas_ai_agent.sub_agents.disclosure_compliance.tools import checklist_loader

    checklist_loader._CHECKLIST_CACHE = None
    mock_path.exists.return_value = True
    with pytest.raises(ValueError, match="Standard 'IFRS 10' not found"):
        load_standard_checklist("IFRS 10")


@patch(
    "veritas_ai_agent.sub_agents.disclosure_compliance.tools.checklist_loader.CHECKLIST_PATH"
)
def test_load_standard_checklist_file_missing(mock_path):
    from veritas_ai_agent.sub_agents.disclosure_compliance.tools import checklist_loader

    checklist_loader._CHECKLIST_CACHE = None
    mock_path.exists.return_value = False
    with pytest.raises(FileNotFoundError):
        load_standard_checklist("IAS 1")
