"""P3-007: ExtraItemDecision endpoints.

eligible=None is valid (undecided) and must be surfaced clearly — undecided items block PVC runs.
source_ref (bill_lines.id) is set by P3-009 when building engine payloads, not stored here.
"""
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from api.deps import DbDep, TenantDep
from api.schemas import APIModel

router = APIRouter(tags=["extra-items"])


async def _assert_contract_tenant(db, contract_id: UUID, tenant_id: UUID):
    row = (
        await db.execute(
            text("SELECT id FROM contracts WHERE id = :id AND tenant_id = :tid"),
            {"id": str(contract_id), "tid": str(tenant_id)},
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Contract not found")


async def _assert_decision_tenant(db, decision_id: UUID, tenant_id: UUID):
    row = (
        await db.execute(
            text("""
                SELECT d.id FROM extra_item_decisions d
                JOIN contracts c ON c.id = d.contract_id
                WHERE d.id = :did AND c.tenant_id = :tid
            """),
            {"did": str(decision_id), "tid": str(tenant_id)},
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Decision not found")


class ExtraItemDecisionIn(APIModel):
    item_id: UUID
    eligible: bool | None = None
    decided_by: str | None = None
    notes: str | None = None


class ExtraItemDecisionUpdate(APIModel):
    eligible: bool | None = None
    decided_by: str | None = None
    notes: str | None = None


class ExtraItemDecisionOut(APIModel):
    id: UUID
    contract_id: UUID
    item_id: UUID
    eligible: bool | None
    decided_by: str | None
    decided_at: str | None
    notes: str | None
    item_code: str | None = None
    description: str | None = None


def _dec_row(r) -> dict:
    return {
        "id": r.id, "contract_id": r.contract_id, "item_id": r.item_id,
        "eligible": r.eligible, "decided_by": r.decided_by,
        "decided_at": r.decided_at.isoformat() if r.decided_at else None,
        "notes": r.notes,
        "item_code": getattr(r, "item_code", None),
        "description": getattr(r, "description", None),
    }


@router.get("/api/contracts/{contract_id}/extra-item-decisions", response_model=list[ExtraItemDecisionOut])
async def list_decisions(contract_id: UUID, tenant_id: TenantDep, db: DbDep):
    await _assert_contract_tenant(db, contract_id, tenant_id)
    rows = (
        await db.execute(
            text("""
                SELECT d.*, ci.item_code, ci.description
                FROM extra_item_decisions d
                JOIN contract_items ci ON ci.id = d.item_id
                WHERE d.contract_id = :cid
                ORDER BY ci.item_code
            """),
            {"cid": str(contract_id)},
        )
    ).all()
    return [_dec_row(r) for r in rows]


@router.post("/api/contracts/{contract_id}/extra-item-decisions", status_code=201, response_model=ExtraItemDecisionOut)
async def create_decision(contract_id: UUID, body: ExtraItemDecisionIn, tenant_id: TenantDep, db: DbDep):
    await _assert_contract_tenant(db, contract_id, tenant_id)

    item = (
        await db.execute(
            text("SELECT id FROM contract_items WHERE id = :iid AND contract_id = :cid"),
            {"iid": str(body.item_id), "cid": str(contract_id)},
        )
    ).one_or_none()
    if item is None:
        raise HTTPException(status_code=422, detail="item_id does not belong to this contract")

    row = (
        await db.execute(
            text("""
                INSERT INTO extra_item_decisions (contract_id, item_id, eligible, decided_by, decided_at, notes)
                VALUES (:cid, :iid, :elig, :by, CASE WHEN :elig IS NOT NULL THEN NOW() ELSE NULL END, :notes)
                ON CONFLICT (contract_id, item_id) DO UPDATE SET
                    eligible = EXCLUDED.eligible,
                    decided_by = EXCLUDED.decided_by,
                    decided_at = EXCLUDED.decided_at,
                    notes = EXCLUDED.notes
                RETURNING *
            """),
            {"cid": str(contract_id), "iid": str(body.item_id), "elig": body.eligible,
             "by": body.decided_by, "notes": body.notes},
        )
    ).one()
    await db.commit()
    return _dec_row(row)


@router.put("/api/extra-item-decisions/{decision_id}", response_model=ExtraItemDecisionOut)
async def update_decision(decision_id: UUID, body: ExtraItemDecisionUpdate, tenant_id: TenantDep, db: DbDep):
    await _assert_decision_tenant(db, decision_id, tenant_id)

    row = (
        await db.execute(
            text("""
                UPDATE extra_item_decisions SET
                    eligible = :elig,
                    decided_by = COALESCE(:by, decided_by),
                    decided_at = CASE WHEN :elig IS NOT NULL THEN NOW() ELSE decided_at END,
                    notes = COALESCE(:notes, notes)
                WHERE id = :did
                RETURNING *
            """),
            {"did": str(decision_id), "elig": body.eligible, "by": body.decided_by, "notes": body.notes},
        )
    ).one()
    await db.commit()
    return _dec_row(row)
