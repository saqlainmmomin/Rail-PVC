"""P3-004: Bills + BillLines + Recoveries endpoints."""
from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from api.deps import DbDep, TenantDep
from api.schemas import APIModel, JsonDecimal

router = APIRouter(tags=["bills"])

_VALID_BILL_STATUS = frozenset({"Draft", "Imported", "Reconciled", "Approved", "Submitted", "Revised", "Locked"})
_VALID_RECOVERY_TYPES = frozenset({"security_deposit", "income_tax", "labour_cess", "water", "other"})


async def _assert_contract_tenant(db, contract_id: UUID, tenant_id: UUID):
    row = (
        await db.execute(
            text("SELECT id FROM contracts WHERE id = :id AND tenant_id = :tid"),
            {"id": str(contract_id), "tid": str(tenant_id)},
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Contract not found")


async def _assert_bill_tenant(db, bill_id: UUID, tenant_id: UUID):
    row = (
        await db.execute(
            text("""
                SELECT b.id FROM running_bills b
                JOIN contracts c ON c.id = b.contract_id
                WHERE b.id = :bid AND c.tenant_id = :tid
            """),
            {"bid": str(bill_id), "tid": str(tenant_id)},
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Bill not found")


# --- Running Bills ---


class BillIn(APIModel):
    bill_number: int
    bill_date: date | None = None
    measurement_date: date
    gross_amount: Decimal | None = None
    net_amount: Decimal | None = None


class BillUpdate(APIModel):
    bill_date: date | None = None
    measurement_date: date | None = None
    gross_amount: Decimal | None = None
    net_amount: Decimal | None = None
    status: str | None = None


class BillOut(APIModel):
    id: UUID
    contract_id: UUID
    bill_number: int
    bill_date: date | None
    measurement_date: date
    gross_amount: JsonDecimal | None
    net_amount: JsonDecimal | None
    status: str
    created_at: str


def _bill_row(r) -> dict:
    return {
        "id": r.id, "contract_id": r.contract_id, "bill_number": r.bill_number,
        "bill_date": r.bill_date, "measurement_date": r.measurement_date,
        "gross_amount": r.gross_amount, "net_amount": r.net_amount,
        "status": r.status, "created_at": r.created_at.isoformat(),
    }


@router.post("/api/contracts/{contract_id}/bills", status_code=201, response_model=BillOut)
async def create_bill(contract_id: UUID, body: BillIn, tenant_id: TenantDep, db: DbDep):
    await _assert_contract_tenant(db, contract_id, tenant_id)
    row = (
        await db.execute(
            text("""
                INSERT INTO running_bills (contract_id, bill_number, bill_date, measurement_date, gross_amount, net_amount)
                VALUES (:cid, :num, :bdate, :mdate, :gross, :net)
                RETURNING *
            """),
            {"cid": str(contract_id), "num": body.bill_number, "bdate": body.bill_date,
             "mdate": body.measurement_date, "gross": body.gross_amount, "net": body.net_amount},
        )
    ).one()
    await db.commit()
    return _bill_row(row)


@router.get("/api/contracts/{contract_id}/bills", response_model=list[BillOut])
async def list_bills(contract_id: UUID, tenant_id: TenantDep, db: DbDep):
    await _assert_contract_tenant(db, contract_id, tenant_id)
    rows = (
        await db.execute(
            text("SELECT * FROM running_bills WHERE contract_id = :cid ORDER BY bill_number"),
            {"cid": str(contract_id)},
        )
    ).all()
    return [_bill_row(r) for r in rows]


@router.get("/api/bills/{bill_id}", response_model=BillOut)
async def get_bill(bill_id: UUID, tenant_id: TenantDep, db: DbDep):
    await _assert_bill_tenant(db, bill_id, tenant_id)
    row = (await db.execute(text("SELECT * FROM running_bills WHERE id = :id"), {"id": str(bill_id)})).one()
    return _bill_row(row)


@router.put("/api/bills/{bill_id}", response_model=BillOut)
async def update_bill(bill_id: UUID, body: BillUpdate, tenant_id: TenantDep, db: DbDep):
    await _assert_bill_tenant(db, bill_id, tenant_id)
    updates = body.model_dump(exclude_none=True)
    if not updates:
        row = (await db.execute(text("SELECT * FROM running_bills WHERE id = :id"), {"id": str(bill_id)})).one()
        return _bill_row(row)

    if "status" in updates and updates["status"] not in _VALID_BILL_STATUS:
        raise HTTPException(status_code=422, detail=f"Invalid status. Must be one of {sorted(_VALID_BILL_STATUS)}")

    set_clauses, params = [], {"id": str(bill_id)}
    for field, value in updates.items():
        if field == "status":
            set_clauses.append(f"{field} = :{field}::bill_status")
        else:
            set_clauses.append(f"{field} = :{field}")
        params[field] = value

    row = (
        await db.execute(
            text(f"UPDATE running_bills SET {', '.join(set_clauses)} WHERE id = :id RETURNING *"),
            params,
        )
    ).one()
    await db.commit()
    return _bill_row(row)


# --- Bill Lines ---


class BillLineIn(APIModel):
    item_id: UUID
    qty_up_to_last: Decimal = Decimal("0")
    qty_since_last: Decimal = Decimal("0")
    qty_up_to_date: Decimal = Decimal("0")
    amount_up_to_last: Decimal = Decimal("0")
    amount_since_last: Decimal = Decimal("0")
    amount_up_to_date: Decimal = Decimal("0")
    special_condition_amount: Decimal = Decimal("0")


class BillLineOut(APIModel):
    id: UUID
    bill_id: UUID
    item_id: UUID
    qty_up_to_last: JsonDecimal
    qty_since_last: JsonDecimal
    qty_up_to_date: JsonDecimal
    amount_up_to_last: JsonDecimal
    amount_since_last: JsonDecimal
    amount_up_to_date: JsonDecimal
    special_condition_amount: JsonDecimal


@router.post("/api/bills/{bill_id}/lines", status_code=201, response_model=BillLineOut)
async def create_bill_line(bill_id: UUID, body: BillLineIn, tenant_id: TenantDep, db: DbDep):
    await _assert_bill_tenant(db, bill_id, tenant_id)
    row = (
        await db.execute(
            text("""
                INSERT INTO bill_lines
                    (bill_id, item_id, qty_up_to_last, qty_since_last, qty_up_to_date,
                     amount_up_to_last, amount_since_last, amount_up_to_date, special_condition_amount)
                VALUES
                    (:bid, :iid, :q_last, :q_since, :q_date,
                     :a_last, :a_since, :a_date, :special)
                ON CONFLICT (bill_id, item_id) DO UPDATE SET
                    qty_up_to_last = EXCLUDED.qty_up_to_last,
                    qty_since_last = EXCLUDED.qty_since_last,
                    qty_up_to_date = EXCLUDED.qty_up_to_date,
                    amount_up_to_last = EXCLUDED.amount_up_to_last,
                    amount_since_last = EXCLUDED.amount_since_last,
                    amount_up_to_date = EXCLUDED.amount_up_to_date,
                    special_condition_amount = EXCLUDED.special_condition_amount
                RETURNING *
            """),
            {
                "bid": str(bill_id), "iid": str(body.item_id),
                "q_last": body.qty_up_to_last, "q_since": body.qty_since_last, "q_date": body.qty_up_to_date,
                "a_last": body.amount_up_to_last, "a_since": body.amount_since_last, "a_date": body.amount_up_to_date,
                "special": body.special_condition_amount,
            },
        )
    ).one()
    await db.commit()
    return {
        "id": row.id, "bill_id": row.bill_id, "item_id": row.item_id,
        "qty_up_to_last": row.qty_up_to_last, "qty_since_last": row.qty_since_last, "qty_up_to_date": row.qty_up_to_date,
        "amount_up_to_last": row.amount_up_to_last, "amount_since_last": row.amount_since_last,
        "amount_up_to_date": row.amount_up_to_date, "special_condition_amount": row.special_condition_amount,
    }


# --- Recoveries ---


class RecoveryIn(APIModel):
    recovery_type: Literal["security_deposit", "income_tax", "labour_cess", "water", "other"]
    amount: Decimal
    affects_pvc_base: bool = False


class RecoveryOut(APIModel):
    id: UUID
    bill_id: UUID
    recovery_type: str
    amount: JsonDecimal
    affects_pvc_base: bool


@router.post("/api/bills/{bill_id}/recoveries", status_code=201, response_model=RecoveryOut)
async def create_recovery(bill_id: UUID, body: RecoveryIn, tenant_id: TenantDep, db: DbDep):
    await _assert_bill_tenant(db, bill_id, tenant_id)
    row = (
        await db.execute(
            text("""
                INSERT INTO recoveries (bill_id, recovery_type, amount, affects_pvc_base)
                VALUES (:bid, :rtype::recovery_type, :amount, :affects)
                RETURNING *
            """),
            {"bid": str(bill_id), "rtype": body.recovery_type, "amount": body.amount, "affects": body.affects_pvc_base},
        )
    ).one()
    await db.commit()
    return {"id": row.id, "bill_id": row.bill_id, "recovery_type": row.recovery_type,
            "amount": row.amount, "affects_pvc_base": row.affects_pvc_base}
