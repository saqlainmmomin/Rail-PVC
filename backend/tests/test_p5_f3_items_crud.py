"""P5-F3: PUT + DELETE /api/schedules/{schedule_id}/items/{item_id}.

Tenant gate is two-step (`_assert_item_under_schedule_for_tenant`):

1. The schedule must belong to the caller's tenant
   (`assert_schedule_belongs_to_tenant`).
2. The item must belong to *that* schedule.

Either failure collapses to a 404 so callers cannot probe foreign IDs
(same discipline as the rest of the contract/bill/item asserts).

Tests exercise the handlers directly against an in-memory aiosqlite
session. The SELECT-back uses Postgres `::text` casts that aiosqlite
can't parse — we catch `OperationalError` and verify the UPDATE/DELETE
ran in the same transaction by reading back raw rows. Same pattern as
`test_p5_001_contracts_put.py`.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.contract_items import (
    ContractItemCreate,
    ContractItemUpdate,
    create_contract_item,
    delete_contract_item,
    update_contract_item,
)
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
        await conn.execute(text(
            "CREATE TABLE contracts (id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL)"
        ))
        await conn.execute(text(
            "CREATE TABLE schedules ("
            " id TEXT PRIMARY KEY, contract_id TEXT NOT NULL"
            ")"
        ))
        await conn.execute(text(
            "CREATE TABLE contract_items ("
            " id TEXT PRIMARY KEY, contract_id TEXT NOT NULL,"
            " schedule_id TEXT NOT NULL, item_code TEXT, description TEXT,"
            " unit TEXT, original_qty NUMERIC, revised_qty NUMERIC,"
            " base_rate NUMERIC, agreement_rate NUMERIC,"
            " is_cement_item INTEGER, steel_subtype TEXT"
            ")"
        ))
        await conn.execute(text(
            "INSERT INTO contracts VALUES"
            " ('c-own', 'tenant-A'), ('c-foreign', 'tenant-B')"
        ))
        await conn.execute(text(
            "INSERT INTO schedules VALUES"
            " ('s-own', 'c-own'), ('s-other-own', 'c-own'),"
            " ('s-foreign', 'c-foreign')"
        ))
        await conn.execute(text(
            "INSERT INTO contract_items"
            " (id, contract_id, schedule_id, item_code, description, unit,"
            "  original_qty, revised_qty, base_rate, agreement_rate,"
            "  is_cement_item, steel_subtype)"
            " VALUES"
            " ('i-own', 'c-own', 's-own', 'A1', 'desc', 'm',"
            "  10, NULL, 100, 95, 0, NULL),"
            " ('i-foreign', 'c-foreign', 's-foreign', 'F1', 'fdesc', 'm',"
            "  10, NULL, 100, 95, 0, NULL)"
        ))
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


# ---------- PUT ----------

async def test_put_valid_update_persists_only_provided_fields(session):
    try:
        await update_contract_item(
            schedule_id="s-own",
            item_id="i-own",
            # aiosqlite doesn't bind `Decimal`; use a plain int — the column
            # is NUMERIC in Postgres and asyncpg binds Decimal there.
            body=ContractItemUpdate(description="renamed"),
            user=_user("tenant-A"),
            session=session,
        )
    except OperationalError:
        # Postgres `::text` cast in SELECT-back is not parseable by aiosqlite.
        # The UPDATE ran in the same transaction — verify by reading back.
        pass

    row = (
        await session.execute(
            text(
                "SELECT description, item_code, agreement_rate FROM contract_items"
                " WHERE id='i-own'"
            )
        )
    ).first()
    assert row is not None
    assert row[0] == "renamed"
    # Unset fields stay put — partial update semantics.
    assert row[1] == "A1"
    assert row[2] == 95


async def test_put_wrong_schedule_id_returns_404(session):
    """Item exists under tenant's other schedule; URL claims s-own → 404
    because the item does not belong to s-own."""
    with pytest.raises(NotFoundProblem) as exc:
        await update_contract_item(
            schedule_id="s-other-own",
            item_id="i-own",
            body=ContractItemUpdate(description="X"),
            user=_user("tenant-A"),
            session=session,
        )
    assert exc.value.status_code == 404


@pytest.mark.parametrize("field", ["item_code", "is_cement_item"])
async def test_put_rejects_null_for_not_null_columns(session, field):
    """REVIEW.md H-2 — item_code and is_cement_item are NOT NULL in the
    migration. Explicit-null payloads must produce a structured 422 (with
    `code=field_not_nullable`), not a raw 500 NOT NULL violation."""
    body = ContractItemUpdate(**{field: None})
    assert field in body.model_fields_set
    with pytest.raises(ValidationProblem) as exc:
        await update_contract_item(
            schedule_id="s-own",
            item_id="i-own",
            body=body,
            user=_user("tenant-A"),
            session=session,
        )
    assert exc.value.status_code == 422
    assert exc.value.extra["field"] == field
    assert exc.value.code == "field_not_nullable"


async def test_put_invalid_steel_subtype_returns_422(session):
    """REVIEW.md M-6 #1 — handler has the gate, no test pins it."""
    with pytest.raises(ValidationProblem) as exc:
        await update_contract_item(
            schedule_id="s-own",
            item_id="i-own",
            body=ContractItemUpdate(steel_subtype="REBAR"),
            user=_user("tenant-A"),
            session=session,
        )
    assert exc.value.status_code == 422
    assert exc.value.extra["field"] == "steel_subtype"


async def test_put_empty_body_is_noop(session):
    """REVIEW.md M-6 #2 — empty payload hits the no-op branch. We can't
    exercise the SELECT-back under aiosqlite (`::text` casts), but we can
    confirm no UPDATE ran by reading back the row directly."""
    from sqlalchemy.exc import OperationalError
    try:
        await update_contract_item(
            schedule_id="s-own",
            item_id="i-own",
            body=ContractItemUpdate(),  # nothing set
            user=_user("tenant-A"),
            session=session,
        )
    except OperationalError:
        pass  # SELECT-back uses ::text casts; no UPDATE was issued.

    row = (
        await session.execute(
            text("SELECT description, item_code, agreement_rate FROM contract_items"
                 " WHERE id='i-own'")
        )
    ).first()
    assert row[0] == "desc"
    assert row[1] == "A1"
    assert row[2] == 95


async def test_put_rejects_cement_steel_conflict(session):
    """REVIEW.md M-3 — the engine treats cement and steel as mutually
    exclusive W-derivation buckets. Backend must enforce the rule, not just
    the frontend banner. PUT that ends up in both buckets → 422."""
    with pytest.raises(ValidationProblem) as exc:
        await update_contract_item(
            schedule_id="s-own",
            item_id="i-own",
            body=ContractItemUpdate(is_cement_item=True, steel_subtype="tmt"),
            user=_user("tenant-A"),
            session=session,
        )
    assert exc.value.status_code == 422
    assert exc.value.code == "cement_steel_conflict"


async def test_post_rejects_cement_steel_conflict(session):
    """Mirror of PUT-side M-3 enforcement on the create path."""
    with pytest.raises(ValidationProblem) as exc:
        await create_contract_item(
            schedule_id="s-own",
            body=ContractItemCreate(
                item_code="C1",
                is_cement_item=True,
                steel_subtype="angles",
            ),
            user=_user("tenant-A"),
            session=session,
        )
    assert exc.value.status_code == 422
    assert exc.value.code == "cement_steel_conflict"


async def test_put_wrong_tenant_returns_404(session):
    """tenant-A cannot touch tenant-B's item via tenant-B's schedule."""
    with pytest.raises(NotFoundProblem) as exc:
        await update_contract_item(
            schedule_id="s-foreign",
            item_id="i-foreign",
            body=ContractItemUpdate(description="HACKED"),
            user=_user("tenant-A"),
            session=session,
        )
    assert exc.value.status_code == 404
    # The schedule gate fires first — message comes from that layer.
    assert exc.value.message == "Schedule not found"


async def test_put_steel_subtype_with_other_fields(session):
    """REVIEW.md M-6 #4 — exercises the SET-clause string-construction path
    where the ENUM cast for steel_subtype coexists with regular `f = :f`
    parameters. The set iteration is unordered (Python sets) — this pins
    that BOTH the cast branch and the plain-binding branch land in the same
    UPDATE. sqlite's CAST to a non-native type clobbers the steel_subtype
    value to NUMERIC affinity, so we assert only what's portable: the plain
    field is written and the UPDATE didn't raise."""
    from sqlalchemy.exc import OperationalError
    try:
        await update_contract_item(
            schedule_id="s-own",
            item_id="i-own",
            body=ContractItemUpdate(steel_subtype="tmt", description="steel-rod"),
            user=_user("tenant-A"),
            session=session,
        )
    except OperationalError:
        pass  # SELECT-back ::text casts

    row = (
        await session.execute(
            text("SELECT description FROM contract_items WHERE id='i-own'")
        )
    ).first()
    assert row[0] == "steel-rod"


# ---------- DELETE ----------

async def test_delete_valid_removes_row(session):
    await delete_contract_item(
        schedule_id="s-own",
        item_id="i-own",
        user=_user("tenant-A"),
        session=session,
    )
    row = (
        await session.execute(
            text("SELECT 1 FROM contract_items WHERE id='i-own'")
        )
    ).first()
    assert row is None


async def test_delete_wrong_schedule_id_returns_404(session):
    with pytest.raises(NotFoundProblem):
        await delete_contract_item(
            schedule_id="s-other-own",
            item_id="i-own",
            user=_user("tenant-A"),
            session=session,
        )
    # And the row is still there — the gate fired before any DELETE ran.
    row = (
        await session.execute(
            text("SELECT 1 FROM contract_items WHERE id='i-own'")
        )
    ).first()
    assert row is not None


async def test_delete_wrong_tenant_returns_404(session):
    with pytest.raises(NotFoundProblem) as exc:
        await delete_contract_item(
            schedule_id="s-foreign",
            item_id="i-foreign",
            user=_user("tenant-A"),
            session=session,
        )
    assert exc.value.status_code == 404
    # tenant-B's item must survive — no cross-tenant deletion.
    row = (
        await session.execute(
            text("SELECT 1 FROM contract_items WHERE id='i-foreign'")
        )
    ).first()
    assert row is not None
