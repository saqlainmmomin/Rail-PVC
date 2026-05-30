"""Index series and observations.

Read endpoints are open to any authenticated user.
Write endpoints (POST /api/indices/{series}/months) are gated behind the
`require_admin` dependency — ordinary authenticated users receive 403.

P3-03 rationale: the backend connects with a privileged DATABASE_URL that
bypasses RLS, so write access cannot be delegated to the database layer.
The admin flag in the `users` table is the only enforcement point.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, field_validator
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth import AuthUser, get_current_user, require_admin
from services.db import get_session
from services.errors import ConflictProblem, NotFoundProblem

router = APIRouter(prefix="/api", tags=["indices"])


class IndexMonthBody(BaseModel):
    month: date
    value: Decimal
    source_ref: str | None = None

    @field_validator("month")
    @classmethod
    def must_be_first_of_month(cls, v: date) -> date:
        if v.day != 1:
            raise ValueError("month must be the first day of the month (e.g. 2026-01-01)")
        return v


@router.get("/index-series")
async def list_series(
    _: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    rows = (
        await session.execute(
            text("""
                SELECT id::text AS id, name, source_publication::text AS source_publication
                FROM index_series
                ORDER BY name
            """)
        )
    ).mappings().all()
    return [dict(r) for r in rows]


@router.get("/index-observations")
async def list_observations(
    series_id: str | None = Query(default=None),
    month_from: date | None = Query(default=None, alias="from"),
    month_to: date | None = Query(default=None, alias="to"),
    _: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    sql = """
        SELECT o.id::text AS id, o.series_id::text AS series_id,
               o.month, o.value, o.revision_flag, o.revised_at, o.created_at
        FROM index_observations o
        WHERE TRUE
    """
    params: dict[str, Any] = {}
    if series_id is not None:
        sql += " AND o.series_id = :sid"
        params["sid"] = series_id
    if month_from is not None:
        sql += " AND o.month >= :mf"
        params["mf"] = month_from
    if month_to is not None:
        sql += " AND o.month <= :mt"
        params["mt"] = month_to
    sql += " ORDER BY o.month"

    rows = (await session.execute(text(sql), params)).mappings().all()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# IDX-3 — GET /api/indices  +  GET /api/indices/{series_name}
# Cleaner URL structure for the frontend Index Manager UI.
# ---------------------------------------------------------------------------


@router.get("/indices")
async def list_index_series(
    _: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    rows = (
        await session.execute(
            text("""
                SELECT id::text AS id, name, source_publication::text AS source_publication
                FROM index_series
                ORDER BY name
            """)
        )
    ).mappings().all()
    return [dict(r) for r in rows]


@router.get("/indices/{series_name}")
async def get_index_series(
    series_name: str,
    _: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    series_row = (
        await session.execute(
            text("""
                SELECT id::text AS id, name, source_publication::text AS source_publication
                FROM index_series
                WHERE name = :name
            """),
            {"name": series_name},
        )
    ).mappings().first()
    if series_row is None:
        raise NotFoundProblem("Index series not found", entity="index_series", name=series_name)

    obs_rows = (
        await session.execute(
            text("""
                SELECT id::text AS id, month, value, source_ref,
                       revision_flag, revised_at, created_at
                FROM index_observations
                WHERE series_id = :sid
                ORDER BY month
            """),
            {"sid": series_row["id"]},
        )
    ).mappings().all()

    return {**dict(series_row), "observations": [dict(r) for r in obs_rows]}


# ---------------------------------------------------------------------------
# IDX-2 — POST /api/indices/{series_name}/months  (admin-only)
# ---------------------------------------------------------------------------


@router.post("/indices/{series_name}/months", status_code=201)
async def add_index_month(
    series_name: str,
    body: IndexMonthBody,
    user: AuthUser = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    series_row = (
        await session.execute(
            text("""
                SELECT id::text AS id
                FROM index_series
                WHERE name = :name
            """),
            {"name": series_name},
        )
    ).mappings().first()
    if series_row is None:
        raise NotFoundProblem("Index series not found", entity="index_series", name=series_name)

    try:
        row = (
            await session.execute(
                text("""
                    INSERT INTO index_observations (series_id, month, value, source_ref)
                    VALUES (:sid, :month, :value, :source_ref)
                    RETURNING id::text AS id, series_id::text AS series_id,
                              month, value, source_ref, revision_flag, created_at
                """),
                {
                    "sid": series_row["id"],
                    "month": body.month,
                    "value": body.value,
                    "source_ref": body.source_ref,
                },
            )
        ).mappings().first()
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise ConflictProblem(
            "An observation for this series and month already exists",
            series=series_name,
            month=str(body.month),
        )

    assert row is not None
    return dict(row)
