"""Engine orchestration for P3-009 POST /pvc-runs.

Collects data from the DB, builds engine payloads, calls calculate_pvc(),
and persists the result. Never swallows validation_errors — 422 if non-empty.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from engine.calculator import calculate_pvc
from engine.quarter import resolve_quarter
from engine.types import (
    BillPayload,
    CarryForwardPayload,
    ExtraItemDecision,
    IndexSnapshot,
    PVCRuleSet as EngineRuleSet,
    PVCRunResult,
)

# GCC 46A.9(2): railway zone → JPC price-reporting city.
ZONE_TO_CITY: dict[str, str] = {
    "NR": "delhi", "NCR": "delhi", "NER": "delhi", "NWR": "delhi",
    "ER": "kolkata", "ECR": "kolkata", "ECOR": "kolkata", "NFR": "kolkata",
    "SER": "kolkata", "SECR": "kolkata",
    "CR": "mumbai", "WR": "mumbai", "WCR": "mumbai",
    "SR": "chennai", "SCR": "chennai", "SWR": "chennai",
}


async def build_bill_payload(db: AsyncSession, contract_id: UUID, bill_id: UUID) -> BillPayload:
    """Assemble BillPayload from DB rows for the given bill.

    Bucket classification:
      on_account_amount  = running_bill.gross_amount
      cement_amount      = sum(bill_lines.amount_since_last) for is_cement_item items
      steel_*_amount     = sum by steel_subtype
      technical_withheld = sum(recoveries.amount) where affects_pvc_base=TRUE
      extra_item_decisions = all decisions for the contract + bill_line amounts
      carry_forwards     = carry_forward records targeting this bill, joined to source bill_lines
    """
    bill_row = (
        await db.execute(
            text("SELECT * FROM running_bills WHERE id = :bid"), {"bid": str(bill_id)}
        )
    ).one()

    lines = (
        await db.execute(
            text("""
                SELECT bl.id, bl.amount_since_last, ci.is_cement_item, ci.steel_subtype
                FROM bill_lines bl
                JOIN contract_items ci ON ci.id = bl.item_id
                WHERE bl.bill_id = :bid
            """),
            {"bid": str(bill_id)},
        )
    ).all()

    cement = Decimal("0")
    steel: dict[str, Decimal] = {"tmt": Decimal("0"), "angles": Decimal("0"), "plates": Decimal("0"), "other_sections": Decimal("0")}
    for ln in lines:
        if ln.is_cement_item:
            cement += ln.amount_since_last
        elif ln.steel_subtype:
            steel[ln.steel_subtype] += ln.amount_since_last

    recoveries = (
        await db.execute(
            text("SELECT amount FROM recoveries WHERE bill_id = :bid AND affects_pvc_base = TRUE"),
            {"bid": str(bill_id)},
        )
    ).all()
    technical_withheld = sum((r.amount for r in recoveries), Decimal("0"))

    decisions_rows = (
        await db.execute(
            text("""
                SELECT d.item_id, d.eligible,
                       bl.id AS bill_line_id, bl.amount_since_last
                FROM extra_item_decisions d
                LEFT JOIN bill_lines bl ON bl.bill_id = :bid AND bl.item_id = d.item_id
                WHERE d.contract_id = :cid
            """),
            {"bid": str(bill_id), "cid": str(contract_id)},
        )
    ).all()
    extra_item_decisions = [
        ExtraItemDecision(
            item_id=str(row.item_id),
            amount=row.amount_since_last or Decimal("0"),
            eligible=row.eligible,
            source_ref=str(row.bill_line_id) if row.bill_line_id else None,
        )
        for row in decisions_rows
    ]

    # Carry-forwards being resolved IN this bill (target_bill_id = bill_id)
    # Joined to source bill's bill_line to get the steel monetary amount (P2-05 / REVIEW HIGH-7).
    cf_rows = (
        await db.execute(
            text("""
                SELECT cf.item_id, cf.recorded_qty, cf.paid_qty_source, cf.steel_subtype,
                       src_bl.id AS src_line_id, src_bl.amount_since_last AS steel_amount
                FROM carry_forwards cf
                JOIN bill_lines src_bl ON src_bl.bill_id = cf.source_bill_id AND src_bl.item_id = cf.item_id
                WHERE cf.contract_id = :cid AND cf.target_bill_id = :bid
            """),
            {"cid": str(contract_id), "bid": str(bill_id)},
        )
    ).all()
    carry_forwards = [
        CarryForwardPayload(
            item_id=str(r.item_id),
            recorded_qty=r.recorded_qty,
            paid_qty_source=r.paid_qty_source,
            amount=r.steel_amount or Decimal("0"),
            steel_subtype=r.steel_subtype,
            source_ref=str(r.src_line_id) if r.src_line_id else None,
        )
        for r in cf_rows
    ]

    # prior_negative_carry_forward: from the previous bill's most recent approved run
    prev_bill = (
        await db.execute(
            text("""
                SELECT id FROM running_bills
                WHERE contract_id = :cid AND bill_number < (SELECT bill_number FROM running_bills WHERE id = :bid)
                ORDER BY bill_number DESC LIMIT 1
            """),
            {"cid": str(contract_id), "bid": str(bill_id)},
        )
    ).one_or_none()

    prior_neg = Decimal("0")
    if prev_bill:
        prev_run = (
            await db.execute(
                text("""
                    SELECT bill_snapshot FROM pvc_runs
                    WHERE bill_id = :pbid AND status = 'Approved'
                    ORDER BY created_at DESC LIMIT 1
                """),
                {"pbid": str(prev_bill.id)},
            )
        ).one_or_none()
        if prev_run and prev_run.bill_snapshot:
            snap = prev_run.bill_snapshot
            if isinstance(snap, str):
                snap = json.loads(snap)
            prior_neg = Decimal(str(snap.get("negative_carry_forward", "0")))

    return BillPayload(
        on_account_amount=bill_row.gross_amount or Decimal("0"),
        cement_amount=cement,
        steel_angles_amount=steel["angles"],
        steel_plates_amount=steel["plates"],
        steel_tmt_amount=steel["tmt"],
        steel_other_amount=steel["other_sections"],
        technical_withheld=technical_withheld,
        extra_item_decisions=extra_item_decisions,
        carry_forwards=carry_forwards,
        measurement_date=bill_row.measurement_date,
        prior_negative_carry_forward=prior_neg,
    )


async def build_index_snapshot(db: AsyncSession, contract_id: UUID, measurement_date: date) -> IndexSnapshot:
    """Build IndexSnapshot from DB observations for the given measurement date.

    Zone-aware: maps railway_zone → JPC city. Tries city-specific series first
    (e.g. steel_tmt_delhi), falls back to generic (steel_tmt) if none found.
    This future-proofs against city-differentiated JPC data (REVIEW HIGH-13).
    """
    contract = (
        await db.execute(
            text("SELECT base_month, railway_zone FROM contracts WHERE id = :cid"),
            {"cid": str(contract_id)},
        )
    ).one()

    _quarter_label, quarter_months = resolve_quarter(measurement_date)
    required_month_dates = [contract.base_month.replace(day=1)] + [
        date(int(m[:4]), int(m[5:7]), 1) for m in quarter_months
    ]

    city = ZONE_TO_CITY.get(str(contract.railway_zone) if contract.railway_zone else "NR", "delhi")

    rows = (
        await db.execute(
            text("""
                SELECT s.name, o.month, o.value
                FROM index_observations o
                JOIN index_series s ON s.id = o.series_id
                WHERE o.month = ANY(:months::date[])
                AND o.value IS NOT NULL
            """),
            {"months": required_month_dates},
        )
    ).all()

    series: dict[str, dict[str, Decimal]] = defaultdict(dict)
    for row in rows:
        month_key = row.month.strftime("%Y-%m")
        series[row.name][month_key] = row.value

    # Alias city-specific series to generic names if city-specific exist
    for generic_name in ("steel_tmt", "steel_angles", "steel_plates", "steel_other_sections"):
        city_name = f"{generic_name}_{city}"
        if city_name in series and generic_name not in series:
            series[generic_name] = series.pop(city_name)

    return IndexSnapshot(base_month=contract.base_month, series=dict(series))


async def persist_run_result(
    db: AsyncSession,
    contract_id: UUID,
    bill_id: UUID,
    rule_set_id: UUID,
    result: PVCRunResult,
    index_snapshot: IndexSnapshot,
    bill_payload: BillPayload,
) -> UUID:
    """Persist pvc_run + pvc_components + revision_snapshot. Returns run_id."""
    import json

    w_deriv_json = json.dumps(result.w_derivation.model_dump(mode="json") if result.w_derivation else {})
    bill_snap_json = json.dumps({
        "gross_amount": str(bill_payload.on_account_amount),
        "measurement_date": bill_payload.measurement_date.isoformat(),
        "negative_carry_forward": str(result.negative_carry_forward),
        "total_pvc": str(result.total_pvc) if result.total_pvc is not None else None,
        "w": str(result.w) if result.w is not None else None,
        "quarter_used": result.quarter_used,
        "quarter_months": result.quarter_months,
    })
    index_snap_json = json.dumps(index_snapshot.model_dump(mode="json"))
    trace_json = json.dumps(result.trace.model_dump(mode="json"))

    run_row = (
        await db.execute(
            text("""
                INSERT INTO pvc_runs
                    (contract_id, bill_id, rule_set_id, index_snapshot, bill_snapshot, w_derivation, trace, status)
                VALUES
                    (:cid, :bid, :rsid, :idx_snap::jsonb, :bill_snap::jsonb, :w_deriv::jsonb, :trace::jsonb, 'Calculated')
                RETURNING id
            """),
            {
                "cid": str(contract_id), "bid": str(bill_id), "rsid": str(rule_set_id),
                "idx_snap": index_snap_json, "bill_snap": bill_snap_json,
                "w_deriv": w_deriv_json, "trace": trace_json,
            },
        )
    ).one()
    run_id = run_row.id

    if result.components:
        for comp in result.components:
            await db.execute(
                text("""
                    INSERT INTO pvc_components
                        (run_id, category, eligible_amount, base_index, current_avg_index, weight, pvc_value)
                    VALUES
                        (:run_id, :cat::pvc_category, :elig, :base_idx, :curr_idx, :weight, :pvc_val)
                """),
                {
                    "run_id": str(run_id), "cat": comp.category,
                    "elig": comp.eligible_amount, "base_idx": comp.base_index,
                    "curr_idx": comp.current_avg_index, "weight": comp.weight,
                    "pvc_val": comp.pvc_value,
                },
            )

    snapshot_data = json.dumps({
        "run_id": str(run_id),
        "w": str(result.w) if result.w is not None else None,
        "total_pvc": str(result.total_pvc) if result.total_pvc is not None else None,
        "negative_carry_forward": str(result.negative_carry_forward),
        "quarter_used": result.quarter_used,
        "components": [c.model_dump(mode="json") for c in result.components],
        "trace": result.trace.model_dump(mode="json"),
        "index_snapshot": index_snapshot.model_dump(mode="json"),
    })
    await db.execute(
        text("INSERT INTO revision_snapshots (run_id, snapshot_data) VALUES (:rid, :snap::jsonb)"),
        {"rid": str(run_id), "snap": snapshot_data},
    )

    await db.commit()
    return run_id


async def get_rule_set(db: AsyncSession, contract_id: UUID) -> tuple[UUID, EngineRuleSet]:
    """Return (rule_set_id, EngineRuleSet) for the latest rule set of this contract."""
    import json as _json

    row = (
        await db.execute(
            text("SELECT * FROM pvc_rule_sets WHERE contract_id = :cid ORDER BY version DESC LIMIT 1"),
            {"cid": str(contract_id)},
        )
    ).one_or_none()
    if row is None:
        raise ValueError("No PVC rule set configured for this contract")

    weights = row.component_weights
    if isinstance(weights, str):
        weights = _json.loads(weights)
    if not isinstance(weights, dict):
        weights = dict(weights)

    return row.id, EngineRuleSet(
        quarter_mode="measurement_date",
        component_weights={k: Decimal(str(v)) for k, v in weights.items()},
        adjustable_fraction=row.adjustable_fraction,
        negative_pvc_policy=row.negative_pvc_policy,
        rounding_mode=row.rounding_mode,
    )
