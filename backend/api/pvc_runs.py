"""P3-009: POST /pvc-runs (engine orchestration)
P3-010: POST /pvc-runs/{id}/approve (immutability enforcement)

Critical invariants:
- validation_errors non-empty → 422, NO persisted run row (REVIEW CRITICAL-4)
- Approved run → PUT attempts return 409 (REVIEW CRITICAL-3)
- Trace JSONB persisted on every successful run (REVIEW HIGH-8)
- source_ref plumbed for extra-items and carry-forwards (REVIEW HIGH-7)
"""
import json
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from api.deps import DbDep, TenantDep
from api.schemas import APIModel, JsonDecimal
from engine.calculator import calculate_pvc
from services.pvc_service import (
    build_bill_payload,
    build_index_snapshot,
    get_rule_set,
    persist_run_result,
)

router = APIRouter(prefix="/api", tags=["pvc-runs"])


async def _assert_contract_tenant(db, contract_id: UUID, tenant_id: UUID):
    row = (
        await db.execute(
            text("SELECT id FROM contracts WHERE id = :id AND tenant_id = :tid"),
            {"id": str(contract_id), "tid": str(tenant_id)},
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Contract not found")


async def _assert_bill_in_contract(db, bill_id: UUID, contract_id: UUID):
    row = (
        await db.execute(
            text("SELECT id FROM running_bills WHERE id = :bid AND contract_id = :cid"),
            {"bid": str(bill_id), "cid": str(contract_id)},
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=422, detail="Bill does not belong to this contract")


async def _assert_run_tenant(db, run_id: UUID, tenant_id: UUID):
    row = (
        await db.execute(
            text("""
                SELECT r.id, r.status FROM pvc_runs r
                JOIN contracts c ON c.id = r.contract_id
                WHERE r.id = :rid AND c.tenant_id = :tid
            """),
            {"rid": str(run_id), "tid": str(tenant_id)},
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="PVC run not found")
    return row.status


class PVCRunRequest(APIModel):
    bill_id: UUID
    idempotency_key: str | None = None


class PVCComponentOut(APIModel):
    category: str
    eligible_amount: JsonDecimal
    base_index: JsonDecimal
    current_avg_index: JsonDecimal
    weight: JsonDecimal
    pvc_value: JsonDecimal


class PVCRunOut(APIModel):
    id: UUID
    contract_id: UUID
    bill_id: UUID
    rule_set_id: UUID
    status: str
    w: JsonDecimal | None
    total_pvc: JsonDecimal | None
    negative_carry_forward: JsonDecimal
    quarter_used: str | None
    components: list[PVCComponentOut]
    validation_errors: list[str]
    created_at: str


class ApproveRequest(APIModel):
    approved_by: str


async def _load_run_out(db, run_id: UUID) -> dict:
    run = (await db.execute(text("SELECT * FROM pvc_runs WHERE id = :id"), {"id": str(run_id)})).one()
    comps = (
        await db.execute(text("SELECT * FROM pvc_components WHERE run_id = :rid"), {"rid": str(run_id)})
    ).all()

    bill_snap = run.bill_snapshot
    if isinstance(bill_snap, str):
        bill_snap = json.loads(bill_snap)
    if not isinstance(bill_snap, dict):
        bill_snap = {}

    w_raw = bill_snap.get("w")
    total_pvc_raw = bill_snap.get("total_pvc")
    w = Decimal(str(w_raw)) if w_raw is not None else None
    total_pvc = Decimal(str(total_pvc_raw)) if total_pvc_raw is not None else None
    neg_cf = Decimal(str(bill_snap.get("negative_carry_forward", "0")))

    return {
        "id": run.id,
        "contract_id": run.contract_id,
        "bill_id": run.bill_id,
        "rule_set_id": run.rule_set_id,
        "status": run.status,
        "w": w,
        "total_pvc": total_pvc,
        "negative_carry_forward": neg_cf,
        "quarter_used": bill_snap.get("quarter_used"),
        "components": [
            {
                "category": c.category,
                "eligible_amount": c.eligible_amount,
                "base_index": c.base_index,
                "current_avg_index": c.current_avg_index,
                "weight": c.weight,
                "pvc_value": c.pvc_value,
            }
            for c in comps
        ],
        "validation_errors": [],
        "created_at": run.created_at.isoformat(),
    }


@router.post("/contracts/{contract_id}/pvc-runs", status_code=201, response_model=PVCRunOut)
async def create_pvc_run(
    contract_id: UUID,
    body: PVCRunRequest,
    tenant_id: TenantDep,
    db: DbDep,
):
    await _assert_contract_tenant(db, contract_id, tenant_id)
    await _assert_bill_in_contract(db, body.bill_id, contract_id)

    # Idempotency: if a Draft run already exists for this bill, return it (REVIEW HIGH-9)
    if body.idempotency_key:
        existing = (
            await db.execute(
                text("""
                    SELECT id FROM pvc_runs
                    WHERE contract_id = :cid AND bill_id = :bid AND status = 'Draft'
                    ORDER BY created_at DESC LIMIT 1
                """),
                {"cid": str(contract_id), "bid": str(body.bill_id)},
            )
        ).one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"message": "Draft run already exists for this bill", "run_id": str(existing.id)},
            )

    # Build engine inputs
    try:
        rule_set_id, engine_rules = await get_rule_set(db, contract_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    bill_payload = await build_bill_payload(db, contract_id, body.bill_id)
    index_snapshot = await build_index_snapshot(db, contract_id, bill_payload.measurement_date)

    # Engine call — pure function, no side effects
    result = calculate_pvc(bill_payload, index_snapshot, engine_rules)

    # CRITICAL: non-empty validation_errors → 422, no row persisted (REVIEW CRITICAL-4)
    if result.validation_errors:
        raise HTTPException(
            status_code=422,
            detail={"validation_errors": result.validation_errors},
        )

    run_id = await persist_run_result(
        db, contract_id, body.bill_id, rule_set_id, result, index_snapshot, bill_payload
    )

    return await _load_run_out(db, run_id)


@router.get("/pvc-runs/{run_id}", response_model=PVCRunOut)
async def get_pvc_run(run_id: UUID, tenant_id: TenantDep, db: DbDep):
    await _assert_run_tenant(db, run_id, tenant_id)
    return await _load_run_out(db, run_id)


@router.post("/pvc-runs/{run_id}/approve", response_model=PVCRunOut)
async def approve_pvc_run(run_id: UUID, body: ApproveRequest, tenant_id: TenantDep, db: DbDep):
    current_status = await _assert_run_tenant(db, run_id, tenant_id)

    if current_status == "Approved":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Run is already approved and cannot be modified",
        )

    # Attempt status update — DB trigger on pvc_runs blocks if already Approved (belt + suspenders)
    await db.execute(
        text("""
            UPDATE pvc_runs
            SET status = 'Approved', approved_by = :by, approved_at = NOW()
            WHERE id = :rid
        """),
        {"rid": str(run_id), "by": body.approved_by},
    )
    await db.commit()

    return await _load_run_out(db, run_id)
