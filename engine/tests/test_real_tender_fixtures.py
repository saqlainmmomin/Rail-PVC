from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from engine import calculate_pvc
from engine.types import BillPayload, IndexSnapshot, PVCRuleSet


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "real_tenders"


def _fixture_paths() -> list[Path]:
    return sorted(FIXTURE_DIR.glob("*.json"))


@pytest.mark.parametrize("path", _fixture_paths(), ids=lambda path: path.stem)
def test_real_tender_fixture_matches_expected_total(path: Path):
    data = json.loads(path.read_text())
    expected = data.get("expected", {})
    assert "total_pvc" in expected, f"{path.name} must define expected.total_pvc"

    result = calculate_pvc(
        bill=BillPayload.model_validate(data["bill"]),
        indices=IndexSnapshot.model_validate(data["indices"]),
        rules=PVCRuleSet.model_validate(data["rules"]),
    )

    assert result.validation_errors == [], f"{path.name} blocked: {result.validation_errors}"
    assert result.total_pvc == Decimal(str(expected["total_pvc"]))


def test_real_tender_fixture_directory_not_empty():
    """Phase 2 acceptance requires at least one real-tender regression fixture."""
    paths = _fixture_paths()
    assert paths, (
        "No real-tender fixtures found in engine/tests/fixtures/real_tenders/. "
        "At least one BCT-24-25-252 fixture (Bill-1/Bill-2) must be present to "
        "guard against engine-level numeric drift."
    )


def test_real_tender_fixture_documents_divergence_where_present():
    """Any fixture whose notes claim a workbook divergence must spell it out."""
    for path in _fixture_paths():
        data = json.loads(path.read_text())
        notes = data.get("notes", {})
        verified = notes.get("verified_against", "")
        if "DIVERGES" in verified or "diverges" in verified.lower():
            assert notes.get("workbook_divergence"), (
                f"{path.name} flags a workbook divergence but does not document it "
                f"in notes.workbook_divergence"
            )
