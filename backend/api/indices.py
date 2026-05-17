"""P3-006: IndexSeries + IndexObservation endpoints.

Write access (POST/PUT on observations) is restricted to service-role paths
by RLS migration 011. Authenticated users can only SELECT.
"""
from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import text

from api.deps import DbDep, TenantDep
from api.schemas import APIModel, JsonDecimal

router = APIRouter(prefix="/api", tags=["indices"])


class IndexSeriesOut(APIModel):
    id: UUID
    name: str
    source_publication: str


class IndexObservationIn(APIModel):
    series_id: UUID
    month: date
    value: Decimal
    source_ref: str | None = None

    def normalized_month(self) -> date:
        return self.month.replace(day=1)


class IndexObservationUpdate(APIModel):
    value: Decimal
    source_ref: str | None = None
    revision_flag: bool = True


class IndexObservationOut(APIModel):
    id: UUID
    series_id: UUID
    month: date
    value: JsonDecimal
    source_ref: str | None
    revision_flag: bool
    revised_at: str | None
    created_at: str


def _obs_row(r) -> dict:
    return {
        "id": r.id, "series_id": r.series_id, "month": r.month, "value": r.value,
        "source_ref": r.source_ref, "revision_flag": r.revision_flag,
        "revised_at": r.revised_at.isoformat() if r.revised_at else None,
        "created_at": r.created_at.isoformat(),
    }


@router.get("/index-series", response_model=list[IndexSeriesOut])
async def list_index_series(tenant_id: TenantDep, db: DbDep):
    rows = (await db.execute(text("SELECT * FROM index_series ORDER BY name"))).all()
    return [{"id": r.id, "name": r.name, "source_publication": r.source_publication} for r in rows]


@router.get("/index-observations", response_model=list[IndexObservationOut])
async def list_index_observations(
    tenant_id: TenantDep,
    db: DbDep,
    series_id: UUID | None = Query(default=None),
    from_month: date | None = Query(default=None, alias="from"),
    to_month: date | None = Query(default=None, alias="to"),
):
    conditions = ["1=1"]
    params: dict = {}
    if series_id:
        conditions.append("series_id = :series_id")
        params["series_id"] = str(series_id)
    if from_month:
        conditions.append("month >= :from_month")
        params["from_month"] = from_month.replace(day=1)
    if to_month:
        conditions.append("month <= :to_month")
        params["to_month"] = to_month.replace(day=1)

    rows = (
        await db.execute(
            text(f"SELECT * FROM index_observations WHERE {' AND '.join(conditions)} ORDER BY month"),
            params,
        )
    ).all()
    return [_obs_row(r) for r in rows]


@router.post("/index-observations", status_code=201, response_model=IndexObservationOut)
async def create_index_observation(body: IndexObservationIn, tenant_id: TenantDep, db: DbDep):
    month = body.normalized_month()
    series = (
        await db.execute(text("SELECT id FROM index_series WHERE id = :sid"), {"sid": str(body.series_id)})
    ).one_or_none()
    if series is None:
        raise HTTPException(status_code=422, detail="Unknown series_id")

    existing = (
        await db.execute(
            text("SELECT id FROM index_observations WHERE series_id = :sid AND month = :m"),
            {"sid": str(body.series_id), "m": month},
        )
    ).one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Observation already exists for (series_id, month). Use PUT to revise.")

    row = (
        await db.execute(
            text("""
                INSERT INTO index_observations (series_id, month, value, source_ref)
                VALUES (:sid, :month, :value, :sref)
                RETURNING *
            """),
            {"sid": str(body.series_id), "month": month, "value": body.value, "sref": body.source_ref},
        )
    ).one()
    await db.commit()
    return _obs_row(row)


@router.put("/index-observations/{obs_id}", response_model=IndexObservationOut)
async def update_index_observation(obs_id: UUID, body: IndexObservationUpdate, tenant_id: TenantDep, db: DbDep):
    existing = (
        await db.execute(text("SELECT id FROM index_observations WHERE id = :id"), {"id": str(obs_id)})
    ).one_or_none()
    if existing is None:
        raise HTTPException(status_code=404, detail="Observation not found")

    row = (
        await db.execute(
            text("""
                UPDATE index_observations
                SET value = :value, source_ref = :sref,
                    revision_flag = :rflag, revised_at = NOW()
                WHERE id = :id
                RETURNING *
            """),
            {"id": str(obs_id), "value": body.value, "sref": body.source_ref, "rflag": body.revision_flag},
        )
    ).one()
    await db.commit()
    return _obs_row(row)
