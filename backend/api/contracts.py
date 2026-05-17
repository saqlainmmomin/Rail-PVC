"""P3-002: Contracts CRUD endpoints."""
from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import field_validator, model_validator
from sqlalchemy import text

from api.deps import DbDep, TenantDep
from api.schemas import APIModel, JsonDecimal

router = APIRouter(prefix="/api/contracts", tags=["contracts"])

_VALID_ZONES = frozenset(
    {"NR", "NCR", "NER", "NWR", "ER", "ECR", "ECOR", "NFR", "SER", "SECR", "CR", "WR", "WCR", "SR", "SCR", "SWR"}
)

_VALID_GST = frozenset({"inclusive", "exclusive"})
_VALID_STATUS = frozenset({"Draft", "Configured", "Active", "Completed", "Archived"})


class ContractIn(APIModel):
    tender_number: str
    agreement_number: str | None = None
    loa_number: str | None = None
    loa_date: date | None = None
    contractor_name: str
    work_description: str | None = None
    contract_value: Decimal | None = None
    bid_amount: Decimal | None = None
    start_date: date | None = None
    completion_date: date | None = None
    base_month: date
    gst_mode: Literal["inclusive", "exclusive"] = "exclusive"
    pvc_applicable: bool = True
    overall_rebate: Decimal = Decimal("0")
    railway_zone: str  # required — 422 if omitted (P3-002 acceptance)

    @field_validator("railway_zone")
    @classmethod
    def _zone_valid(cls, v: str) -> str:
        if v not in _VALID_ZONES:
            raise ValueError(f"railway_zone must be one of {sorted(_VALID_ZONES)}")
        return v

    @field_validator("base_month")
    @classmethod
    def _base_month_first_of_month(cls, v: date) -> date:
        return v.replace(day=1)


class ContractOut(APIModel):
    id: UUID
    tenant_id: UUID
    tender_number: str
    agreement_number: str | None
    loa_number: str | None
    loa_date: date | None
    contractor_name: str
    work_description: str | None
    contract_value: JsonDecimal | None
    bid_amount: JsonDecimal | None
    start_date: date | None
    completion_date: date | None
    base_month: date
    gst_mode: str
    pvc_applicable: bool
    overall_rebate: JsonDecimal
    status: str
    railway_zone: str
    created_at: str


class ContractUpdate(APIModel):
    agreement_number: str | None = None
    loa_number: str | None = None
    loa_date: date | None = None
    contractor_name: str | None = None
    work_description: str | None = None
    contract_value: Decimal | None = None
    bid_amount: Decimal | None = None
    start_date: date | None = None
    completion_date: date | None = None
    gst_mode: Literal["inclusive", "exclusive"] | None = None
    pvc_applicable: bool | None = None
    overall_rebate: Decimal | None = None
    status: str | None = None
    railway_zone: str | None = None

    @field_validator("railway_zone")
    @classmethod
    def _zone_valid(cls, v: str | None) -> str | None:
        if v is not None and v not in _VALID_ZONES:
            raise ValueError(f"railway_zone must be one of {sorted(_VALID_ZONES)}")
        return v

    @field_validator("status")
    @classmethod
    def _status_valid(cls, v: str | None) -> str | None:
        if v is not None and v not in _VALID_STATUS:
            raise ValueError(f"status must be one of {sorted(_VALID_STATUS)}")
        return v


def _row_to_out(row) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "tender_number": row.tender_number,
        "agreement_number": row.agreement_number,
        "loa_number": row.loa_number,
        "loa_date": row.loa_date,
        "contractor_name": row.contractor_name,
        "work_description": row.work_description,
        "contract_value": row.contract_value,
        "bid_amount": row.bid_amount,
        "start_date": row.start_date,
        "completion_date": row.completion_date,
        "base_month": row.base_month,
        "gst_mode": row.gst_mode,
        "pvc_applicable": row.pvc_applicable,
        "overall_rebate": row.overall_rebate,
        "status": row.status,
        "railway_zone": row.railway_zone,
        "created_at": row.created_at.isoformat(),
    }


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ContractOut)
async def create_contract(body: ContractIn, tenant_id: TenantDep, db: DbDep):
    row = (
        await db.execute(
            text("""
                INSERT INTO contracts (
                    tenant_id, tender_number, agreement_number, loa_number, loa_date,
                    contractor_name, work_description, contract_value, bid_amount,
                    start_date, completion_date, base_month, gst_mode, pvc_applicable,
                    overall_rebate, railway_zone
                ) VALUES (
                    :tenant_id, :tender_number, :agreement_number, :loa_number, :loa_date,
                    :contractor_name, :work_description, :contract_value, :bid_amount,
                    :start_date, :completion_date, :base_month, :gst_mode, :pvc_applicable,
                    :overall_rebate, :railway_zone::railway_zone
                )
                RETURNING *
            """),
            {
                "tenant_id": str(tenant_id),
                "tender_number": body.tender_number,
                "agreement_number": body.agreement_number,
                "loa_number": body.loa_number,
                "loa_date": body.loa_date,
                "contractor_name": body.contractor_name,
                "work_description": body.work_description,
                "contract_value": body.contract_value,
                "bid_amount": body.bid_amount,
                "start_date": body.start_date,
                "completion_date": body.completion_date,
                "base_month": body.base_month,
                "gst_mode": body.gst_mode,
                "pvc_applicable": body.pvc_applicable,
                "overall_rebate": body.overall_rebate,
                "railway_zone": body.railway_zone,
            },
        )
    ).one()
    await db.commit()
    return _row_to_out(row)


@router.get("", response_model=list[ContractOut])
async def list_contracts(tenant_id: TenantDep, db: DbDep):
    rows = (
        await db.execute(
            text("SELECT * FROM contracts WHERE tenant_id = :tid ORDER BY created_at DESC"),
            {"tid": str(tenant_id)},
        )
    ).all()
    return [_row_to_out(r) for r in rows]


@router.get("/{contract_id}", response_model=ContractOut)
async def get_contract(contract_id: UUID, tenant_id: TenantDep, db: DbDep):
    row = (
        await db.execute(
            text("SELECT * FROM contracts WHERE id = :id AND tenant_id = :tid"),
            {"id": str(contract_id), "tid": str(tenant_id)},
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")
    return _row_to_out(row)


@router.put("/{contract_id}", response_model=ContractOut)
async def update_contract(contract_id: UUID, body: ContractUpdate, tenant_id: TenantDep, db: DbDep):
    existing = (
        await db.execute(
            text("SELECT * FROM contracts WHERE id = :id AND tenant_id = :tid"),
            {"id": str(contract_id), "tid": str(tenant_id)},
        )
    ).one_or_none()
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")

    updates = body.model_dump(exclude_none=True)
    if not updates:
        return _row_to_out(existing)

    set_clauses = []
    params: dict = {"id": str(contract_id), "tid": str(tenant_id)}
    for field, value in updates.items():
        if field == "railway_zone":
            set_clauses.append(f"{field} = :{field}::railway_zone")
        elif field == "gst_mode":
            set_clauses.append(f"{field} = :{field}::gst_mode")
        elif field == "status":
            set_clauses.append(f"{field} = :{field}::contract_status")
        else:
            set_clauses.append(f"{field} = :{field}")
        params[field] = value

    row = (
        await db.execute(
            text(f"UPDATE contracts SET {', '.join(set_clauses)} WHERE id = :id AND tenant_id = :tid RETURNING *"),
            params,
        )
    ).one()
    await db.commit()
    return _row_to_out(row)
