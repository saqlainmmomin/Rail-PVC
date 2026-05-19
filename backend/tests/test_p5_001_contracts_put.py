"""P5-001: PUT /api/contracts/{id} — partial update with tenant gate +
input validation. We exercise the handler function directly with an
in-memory aiosqlite session; the contracts table is a stub with only the
columns the handler touches. The Postgres `::text` casts in the
SELECT-back path are exercised in integration; here we focus on the
validation/auth surface the route owns and on dynamic SET-clause
construction from `model_fields_set`."""
from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.contracts import ContractUpdate, update_contract
from services.auth import AuthUser
from services.errors import NotFoundProblem, ValidationProblem


def _user(tenant: str = "tenant-A") -> AuthUser:
    return AuthUser(
        user_id="user-1",
        tenant_id=tenant,
        auth_id="auth-1",
        email="t@example.com",
        display_name="t",
    )


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        # Minimum schema the handler touches for tenant gate + validation.
        await conn.execute(text(
            "CREATE TABLE contracts ("
            " id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL,"
            " contractor_name TEXT, railway_zone TEXT, base_month TEXT,"
            " gst_mode TEXT, status TEXT"
            ")"
        ))
        await conn.execute(text(
            "INSERT INTO contracts (id, tenant_id, contractor_name, railway_zone,"
            " base_month, gst_mode, status) VALUES"
            " ('c-own', 'tenant-A', 'ACME', 'NR', '2025-04-01', 'exclusive', 'Draft'),"
            " ('c-foreign', 'tenant-B', 'OTHER', 'NR', '2025-04-01', 'exclusive', 'Draft')"
        ))
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


async def test_wrong_tenant_returns_404(session):
    """Wrong-tenant contract collapses to NotFoundProblem so callers cannot
    probe foreign IDs — same rationale as P3-BF-1."""
    with pytest.raises(NotFoundProblem) as exc:
        await update_contract(
            contract_id="c-foreign",
            body=ContractUpdate(contractor_name="HACKED"),
            user=_user("tenant-A"),
            session=session,
        )
    assert exc.value.status_code == 404
    assert exc.value.message == "Contract not found"


async def test_unknown_contract_returns_404(session):
    with pytest.raises(NotFoundProblem):
        await update_contract(
            contract_id="c-missing",
            body=ContractUpdate(contractor_name="X"),
            user=_user("tenant-A"),
            session=session,
        )


async def test_invalid_railway_zone_raises_422(session):
    with pytest.raises(ValidationProblem) as exc:
        await update_contract(
            contract_id="c-own",
            body=ContractUpdate(railway_zone="XX"),
            user=_user("tenant-A"),
            session=session,
        )
    assert exc.value.status_code == 422
    assert exc.value.extra["field"] == "railway_zone"


async def test_base_month_must_be_first_of_month(session):
    from datetime import date
    with pytest.raises(ValidationProblem) as exc:
        await update_contract(
            contract_id="c-own",
            body=ContractUpdate(base_month=date(2025, 4, 15)),
            user=_user("tenant-A"),
            session=session,
        )
    assert exc.value.status_code == 422
    assert exc.value.extra["field"] == "base_month"


def test_model_fields_set_excludes_unset_fields():
    """The partial-update SET clause is built from `model_fields_set`. An
    Optional field that is not in the payload must NOT appear in the SET
    clause, otherwise it would NULL out the column. This pins the contract
    that the handler relies on."""
    body = ContractUpdate(contractor_name="ACME")
    assert body.model_fields_set == {"contractor_name"}
    # All other fields default to None but are NOT in model_fields_set.
    assert "loa_number" not in body.model_fields_set
    assert "railway_zone" not in body.model_fields_set


async def test_valid_update_writes_only_provided_fields(session):
    """End-to-end happy path on the writeable side of the handler: a partial
    update with only one field flips that column and leaves the rest alone."""
    # The SELECT-back at the end of the handler uses Postgres `::text` casts
    # that aiosqlite cannot parse — accept the StatementError but verify the
    # UPDATE itself landed by reading back manually.
    from sqlalchemy.exc import OperationalError
    try:
        await update_contract(
            contract_id="c-own",
            body=ContractUpdate(contractor_name="ACME-RENAMED"),
            user=_user("tenant-A"),
            session=session,
        )
    except OperationalError:
        # Expected: `railway_zone::text` is invalid in sqlite. The UPDATE
        # ran in the same transaction — verify it persisted.
        pass

    row = (
        await session.execute(
            text("SELECT contractor_name, railway_zone, base_month FROM contracts WHERE id='c-own'")
        )
    ).first()
    assert row is not None
    assert row[0] == "ACME-RENAMED"
    # Unchanged fields stay put — the partial update did not touch them.
    assert row[1] == "NR"
    assert row[2] == "2025-04-01"
