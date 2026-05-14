from engine.types import BillPayload, IndexSnapshot, PVCRuleSet, PVCRunResult


def calculate_pvc(
    bill: BillPayload,
    indices: IndexSnapshot,
    rules: PVCRuleSet,
) -> PVCRunResult:
    """
    Pure function — same inputs always produce same output.
    No database calls. No HTTP calls. No global state.
    If validation_errors is non-empty, total_pvc is None and the run is blocked.
    """
    return PVCRunResult(
        w=None,
        w_derivation=None,
        components=[],
        total_pvc=None,
        quarter_used=None,
        quarter_months=[],
        trace={},
        validation_errors=["Engine not yet implemented — Phase 2"],
    )
