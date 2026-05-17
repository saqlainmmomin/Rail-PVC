"""P3-003: Schedules + ContractItems endpoints."""
from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import field_validator
from sqlalchemy import text

from api.deps import DbDep, TenantDep
from api.schemas import APIModel, JsonDecimal

router = APIRouter(tags=["schedules"])

_VALID_SCHEDULE_TYPES = frozenset({"DSR", "NS", "ExtraNS"})
_VALID_STEEL_SUBTYPES = frozenset({"angles", "plates", "other_sections", "tmt"})


async def _assert_contract_tenant(db, contract_id: UUID, tenant_id: UUID):
    row = (
        await db.execute(
            text("SELECT id FROM contracts WHERE id = :id AND tenant_id = :tid"),
            {"id": str(contract_id), "tid": str(tenant_id)},
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")


async def _assert_schedule_tenant(db, schedule_id: UUID, tenant_id: UUID) -> UUID:
    """Returns contract_id if found."""
    row = (
        await db.execute(
            text("""
                SELECT s.id, s.contract_id FROM schedules s
                JOIN contracts c ON c.id = s.contract_id
                WHERE s.id = :sid AND c.tenant_id = :tid
            """),
            {"sid": str(schedule_id), "tid": str(tenant_id)},
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")
    return row.contract_id


# --- Schedules ---


class ScheduleIn(APIModel):
    name: str
    schedule_type: Literal["DSR", "NS", "ExtraNS"]
    bid_discount_pct: Decimal = Decimal("0")


class ScheduleOut(APIModel):
    id: UUID
    contract_id: UUID
    name: str
    schedule_type: str
    bid_discount_pct: JsonDecimal
    created_at: str


@router.post("/api/contracts/{contract_id}/schedules", status_code=201, response_model=ScheduleOut)
async def create_schedule(contract_id: UUID, body: ScheduleIn, tenant_id: TenantDep, db: DbDep):
    await _assert_contract_tenant(db, contract_id, tenant_id)
    row = (
        await db.execute(
            text("""
                INSERT INTO schedules (contract_id, name, schedule_type, bid_discount_pct)
                VALUES (:cid, :name, :stype::schedule_type, :disc)
                RETURNING *
            """),
            {"cid": str(contract_id), "name": body.name, "stype": body.schedule_type, "disc": body.bid_discount_pct},
        )
    ).one()
    await db.commit()
    return {"id": row.id, "contract_id": row.contract_id, "name": row.name, "schedule_type": row.schedule_type,
            "bid_discount_pct": row.bid_discount_pct, "created_at": row.created_at.isoformat()}


@router.get("/api/contracts/{contract_id}/schedules", response_model=list[ScheduleOut])
async def list_schedules(contract_id: UUID, tenant_id: TenantDep, db: DbDep):
    await _assert_contract_tenant(db, contract_id, tenant_id)
    rows = (
        await db.execute(
            text("SELECT * FROM schedules WHERE contract_id = :cid ORDER BY created_at"),
            {"cid": str(contract_id)},
        )
    ).all()
    return [{"id": r.id, "contract_id": r.contract_id, "name": r.name, "schedule_type": r.schedule_type,
             "bid_discount_pct": r.bid_discount_pct, "created_at": r.created_at.isoformat()} for r in rows]


# --- ContractItems ---


class ContractItemIn(APIModel):
    item_code: str
    description: str | None = None
    unit: str | None = None
    original_qty: Decimal | None = None
    revised_qty: Decimal | None = None
    base_rate: Decimal | None = None
    agreement_rate: Decimal | None = None
    is_cement_item: bool = False
    steel_subtype: str | None = None

    @field_validator("steel_subtype")
    @classmethod
    def _subtype_valid(cls, v: str | None) -> str | None:
        if v is not None and v not in _VALID_STEEL_SUBTYPES:
            raise ValueError(f"steel_subtype must be one of {sorted(_VALID_STEEL_SUBTYPES)} or null")
        return v


class ContractItemOut(APIModel):
    id: UUID
    contract_id: UUID
    schedule_id: UUID
    item_code: str
    description: str | None
    unit: str | None
    original_qty: JsonDecimal | None
    revised_qty: JsonDecimal | None
    base_rate: JsonDecimal | None
    agreement_rate: JsonDecimal | None
    is_cement_item: bool
    steel_subtype: str | None
    created_at: str


def _item_row_to_dict(r) -> dict:
    return {
        "id": r.id, "contract_id": r.contract_id, "schedule_id": r.schedule_id,
        "item_code": r.item_code, "description": r.description, "unit": r.unit,
        "original_qty": r.original_qty, "revised_qty": r.revised_qty,
        "base_rate": r.base_rate, "agreement_rate": r.agreement_rate,
        "is_cement_item": r.is_cement_item, "steel_subtype": r.steel_subtype,
        "created_at": r.created_at.isoformat(),
    }


@router.post("/api/schedules/{schedule_id}/items", status_code=201, response_model=ContractItemOut)
async def create_item(schedule_id: UUID, body: ContractItemIn, tenant_id: TenantDep, db: DbDep):
    contract_id = await _assert_schedule_tenant(db, schedule_id, tenant_id)
    row = (
        await db.execute(
            text("""
                INSERT INTO contract_items
                    (contract_id, schedule_id, item_code, description, unit,
                     original_qty, revised_qty, base_rate, agreement_rate,
                     is_cement_item, steel_subtype)
                VALUES
                    (:cid, :sid, :code, :desc, :unit,
                     :orig_qty, :rev_qty, :base_rate, :agr_rate,
                     :is_cement, :steel_subtype::steel_subtype)
                RETURNING *
            """),
            {
                "cid": str(contract_id), "sid": str(schedule_id),
                "code": body.item_code, "desc": body.description, "unit": body.unit,
                "orig_qty": body.original_qty, "rev_qty": body.revised_qty,
                "base_rate": body.base_rate, "agr_rate": body.agreement_rate,
                "is_cement": body.is_cement_item, "steel_subtype": body.steel_subtype,
            },
        )
    ).one()
    await db.commit()
    return _item_row_to_dict(row)


@router.get("/api/contracts/{contract_id}/items", response_model=list[ContractItemOut])
async def list_items(contract_id: UUID, tenant_id: TenantDep, db: DbDep):
    await _assert_contract_tenant(db, contract_id, tenant_id)
    rows = (
        await db.execute(
            text("SELECT * FROM contract_items WHERE contract_id = :cid ORDER BY created_at"),
            {"cid": str(contract_id)},
        )
    ).all()
    return [_item_row_to_dict(r) for r in rows]
