"""P3-005: CarryForward endpoints.

paid_ratio is ALWAYS server-derived from paid_qty / recorded_qty.
Clients supply paid_qty only; ratio is never accepted from the wire.
"""
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import field_validator
from sqlalchemy import text

from api.deps import DbDep, TenantDep
from api.schemas import APIModel, JsonDecimal

router = APIRouter(tags=["carry-forwards"])


async def _assert_contract_tenant(db, contract_id: UUID, tenant_id: UUID):
    row = (
        await db.execute(
            text("SELECT id FROM contracts WHERE id = :id AND tenant_id = :tid"),
            {"id": str(contract_id), "tid": str(tenant_id)},
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Contract not found")


async def _assert_cf_tenant(db, cf_id: UUID, tenant_id: UUID):
    row = (
        await db.execute(
            text("""
                SELECT cf.id, cf.recorded_qty FROM carry_forwards cf
                JOIN contracts c ON c.id = cf.contract_id
                WHERE cf.id = :cfid AND c.tenant_id = :tid
            """),
            {"cfid": str(cf_id), "tid": str(tenant_id)},
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Carry-forward not found")
    return row.recorded_qty


class CarryForwardOut(APIModel):
    id: UUID
    contract_id: UUID
    item_id: UUID
    source_bill_id: UUID
    target_bill_id: UUID | None
    recorded_qty: JsonDecimal
    paid_qty_source: JsonDecimal
    paid_ratio: JsonDecimal
    carry_qty: JsonDecimal
    steel_subtype: str | None
    created_at: str


class CarryForwardUpdate(APIModel):
    paid_qty_source: Decimal
    target_bill_id: UUID | None = None

    @field_validator("paid_qty_source")
    @classmethod
    def _non_negative(cls, v: Decimal) -> Decimal:
        if v < Decimal("0"):
            raise ValueError("paid_qty_source must be >= 0")
        return v


def _cf_row(r) -> dict:
    return {
        "id": r.id, "contract_id": r.contract_id, "item_id": r.item_id,
        "source_bill_id": r.source_bill_id, "target_bill_id": r.target_bill_id,
        "recorded_qty": r.recorded_qty, "paid_qty_source": r.paid_qty_source,
        "paid_ratio": r.paid_ratio, "carry_qty": r.carry_qty,
        "steel_subtype": r.steel_subtype, "created_at": r.created_at.isoformat(),
    }


@router.get("/api/contracts/{contract_id}/carry-forwards", response_model=list[CarryForwardOut])
async def list_carry_forwards(contract_id: UUID, tenant_id: TenantDep, db: DbDep):
    await _assert_contract_tenant(db, contract_id, tenant_id)
    rows = (
        await db.execute(
            text("SELECT * FROM carry_forwards WHERE contract_id = :cid ORDER BY created_at"),
            {"cid": str(contract_id)},
        )
    ).all()
    return [_cf_row(r) for r in rows]


@router.put("/api/carry-forwards/{cf_id}", response_model=CarryForwardOut)
async def update_carry_forward(cf_id: UUID, body: CarryForwardUpdate, tenant_id: TenantDep, db: DbDep):
    recorded_qty = await _assert_cf_tenant(db, cf_id, tenant_id)

    if body.paid_qty_source > recorded_qty:
        raise HTTPException(
            status_code=422,
            detail=f"paid_qty_source ({body.paid_qty_source}) cannot exceed recorded_qty ({recorded_qty})",
        )

    # paid_ratio always server-derived (REVIEW HIGH-11)
    paid_ratio = body.paid_qty_source / recorded_qty
    carry_qty = recorded_qty - body.paid_qty_source

    params: dict = {
        "cfid": str(cf_id),
        "paid_qty": body.paid_qty_source,
        "paid_ratio": paid_ratio,
        "carry_qty": carry_qty,
    }
    extra = ""
    if body.target_bill_id is not None:
        extra = ", target_bill_id = :target_bill_id"
        params["target_bill_id"] = str(body.target_bill_id)

    row = (
        await db.execute(
            text(f"""
                UPDATE carry_forwards
                SET paid_qty_source = :paid_qty, paid_ratio = :paid_ratio, carry_qty = :carry_qty{extra}
                WHERE id = :cfid
                RETURNING *
            """),
            params,
        )
    ).one()
    await db.commit()
    return _cf_row(row)
