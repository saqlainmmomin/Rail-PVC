"""IDX-2..3: index series list/detail (GET) + admin monthly entry (POST).

Read routes (IDX-3) use the same boundary-mock pattern as the SH-P5 tests
(AsyncSession stubbed at session.execute). The POST (IDX-2) additionally
exercises the admin gate and the duplicate-month 409 path.

The test_p3_03 regression remains unchanged — it asserts no write endpoints
on /api/index-observations and /api/index-series. The new POST is at
/api/indices/{series_name}/months (different path) and is intentionally
excluded from those checks.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.indices import add_index_month, get_index_series, list_index_series
from services.auth import AuthUser
from services.errors import ConflictProblem, ForbiddenProblem, NotFoundProblem


def _user(*, is_admin: bool = False) -> AuthUser:
    return AuthUser(
        user_id="user-1",
        tenant_id="tenant-A",
        auth_id="auth-1",
        email="t@example.com",
        display_name="t@example.com",
        is_admin=is_admin,
    )


def _session_with(*results: tuple[str, object]) -> AsyncMock:
    """Stub AsyncSession. Each tuple: ("first", row|None) or ("all", list)."""
    session = AsyncMock()
    mocked = []
    for kind, payload in results:
        result = MagicMock()
        mappings = MagicMock()
        if kind == "first":
            mappings.first.return_value = payload
            result.first.return_value = payload
        elif kind == "all":
            mappings.all.return_value = payload
            result.all.return_value = payload
        result.mappings.return_value = mappings
        mocked.append(result)
    session.execute = AsyncMock(side_effect=mocked)
    return session


# ---------------------------------------------------------------------------
# IDX-3 — GET /api/indices
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_index_series_returns_rows():
    series_rows = [
        {"id": "s-1", "name": "wpi_all_commodities", "source_publication": "RBI"},
        {"id": "s-2", "name": "steel_tmt", "source_publication": "JPC"},
    ]
    session = _session_with(("all", series_rows))

    out = await list_index_series(_=_user(), session=session)

    assert out == series_rows
    assert session.execute.await_count == 1


@pytest.mark.asyncio
async def test_list_index_series_empty():
    session = _session_with(("all", []))

    out = await list_index_series(_=_user(), session=session)

    assert out == []


# ---------------------------------------------------------------------------
# IDX-3 — GET /api/indices/{series_name}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_index_series_returns_series_with_observations():
    series_row = {"id": "s-1", "name": "wpi_all_commodities", "source_publication": "RBI"}
    obs_rows = [
        {
            "id": "o-1", "month": date(2026, 1, 1), "value": Decimal("147.3"),
            "source_ref": "BCT-24-25-252", "revision_flag": False,
            "revised_at": None, "created_at": datetime(2026, 5, 1),
        },
        {
            "id": "o-2", "month": date(2026, 2, 1), "value": Decimal("148.1"),
            "source_ref": None, "revision_flag": False,
            "revised_at": None, "created_at": datetime(2026, 5, 15),
        },
    ]
    session = _session_with(("first", series_row), ("all", obs_rows))

    out = await get_index_series(series_name="wpi_all_commodities", _=_user(), session=session)

    assert out["id"] == "s-1"
    assert out["name"] == "wpi_all_commodities"
    assert out["observations"] == obs_rows
    assert session.execute.await_count == 2


@pytest.mark.asyncio
async def test_get_index_series_no_observations_returns_empty_list():
    series_row = {"id": "s-1", "name": "wpi_all_commodities", "source_publication": "RBI"}
    session = _session_with(("first", series_row), ("all", []))

    out = await get_index_series(series_name="wpi_all_commodities", _=_user(), session=session)

    assert out["observations"] == []
    assert session.execute.await_count == 2


@pytest.mark.asyncio
async def test_get_index_series_unknown_name_raises_not_found():
    session = _session_with(("first", None))

    with pytest.raises(NotFoundProblem) as exc:
        await get_index_series(series_name="no_such_series", _=_user(), session=session)

    assert exc.value.status_code == 404
    assert exc.value.extra["entity"] == "index_series"
    assert exc.value.extra["name"] == "no_such_series"
    assert session.execute.await_count == 1


# ---------------------------------------------------------------------------
# IDX-2 — POST /api/indices/{series_name}/months (admin-only)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_index_month_admin_inserts_and_returns_row():
    from api.indices import IndexMonthBody

    series_row = {"id": "s-1"}
    inserted = {
        "id": "o-new",
        "series_id": "s-1",
        "month": date(2026, 5, 1),
        "value": Decimal("149.0"),
        "source_ref": "manual",
        "revision_flag": False,
        "created_at": datetime(2026, 5, 30),
    }
    session = _session_with(("first", series_row), ("first", inserted))

    body = IndexMonthBody(month=date(2026, 5, 1), value=Decimal("149.0"), source_ref="manual")
    out = await add_index_month(
        series_name="wpi_all_commodities",
        body=body,
        user=_user(is_admin=True),
        session=session,
    )

    assert out == inserted
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_add_index_month_non_admin_raises_forbidden():
    """require_admin dependency raises ForbiddenProblem before hitting DB."""
    from services.auth import require_admin

    with pytest.raises(ForbiddenProblem) as exc:
        await require_admin(user=_user(is_admin=False))

    assert exc.value.status_code == 403
    assert exc.value.code == "forbidden"


@pytest.mark.asyncio
async def test_add_index_month_unknown_series_raises_not_found():
    from api.indices import IndexMonthBody

    session = _session_with(("first", None))
    body = IndexMonthBody(month=date(2026, 5, 1), value=Decimal("149.0"))

    with pytest.raises(NotFoundProblem) as exc:
        await add_index_month(
            series_name="no_such_series",
            body=body,
            user=_user(is_admin=True),
            session=session,
        )

    assert exc.value.status_code == 404
    assert exc.value.extra["entity"] == "index_series"


@pytest.mark.asyncio
async def test_add_index_month_duplicate_raises_conflict():
    """UNIQUE(series_id, month) violation → 409 ConflictProblem."""
    from sqlalchemy.exc import IntegrityError

    from api.indices import IndexMonthBody

    series_row = {"id": "s-1"}
    session = _session_with(("first", series_row))
    # Second execute raises IntegrityError (duplicate key)
    session.execute = AsyncMock(
        side_effect=[
            _session_with(("first", series_row)).execute.side_effect[0]
            if False
            else _make_first_result(series_row),
            IntegrityError("duplicate", {}, Exception()),
        ]
    )

    body = IndexMonthBody(month=date(2026, 1, 1), value=Decimal("147.3"))

    with pytest.raises(ConflictProblem) as exc:
        await add_index_month(
            series_name="wpi_all_commodities",
            body=body,
            user=_user(is_admin=True),
            session=session,
        )

    assert exc.value.status_code == 409
    assert exc.value.extra["month"] == "2026-01-01"
    session.rollback.assert_awaited_once()


def _make_first_result(payload: object) -> MagicMock:
    result = MagicMock()
    mappings = MagicMock()
    mappings.first.return_value = payload
    result.mappings.return_value = mappings
    result.first.return_value = payload
    return result


@pytest.mark.asyncio
async def test_index_month_body_rejects_non_first_of_month():
    """Pydantic validator blocks day != 1 before the route body is processed."""
    import pydantic

    from api.indices import IndexMonthBody

    with pytest.raises(pydantic.ValidationError):
        IndexMonthBody(month=date(2026, 5, 15), value=Decimal("149.0"))
