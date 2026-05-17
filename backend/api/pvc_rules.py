"""P3-008: PVCRuleSet endpoints.

component_weights validation mirrors engine._weights_complete_and_known:
exactly {"labour", "plant", "fuel", "materials"} — no missing, no extra, no negatives.
"""
from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import field_validator
from sqlalchemy import text

from api.deps import DbDep, TenantDep
from api.schemas import APIModel, JsonDecimal

router = APIRouter(tags=["pvc-rules"])

_REQUIRED_WEIGHT_KEYS = frozenset({"labour", "plant", "fuel", "materials"})


async def _assert_contract_tenant(db, contract_id: UUID, tenant_id: UUID):
    row = (
        await db.execute(
            text("SELECT id FROM contracts WHERE id = :id AND tenant_id = :tid"),
            {"id": str(contract_id), "tid": str(tenant_id)},
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Contract not found")


class PVCRuleSetIn(APIModel):
    quarter_mode: Literal["measurement_date"] = "measurement_date"
    component_weights: dict[str, Decimal]
    extra_item_policy: Literal["exclude_by_default", "include_by_default"] = "exclude_by_default"
    adjustable_fraction: Decimal = Decimal("0.85")
    rounding_mode: Literal["round_2", "truncate_2"] = "round_2"
    negative_pvc_policy: Literal["allow", "block", "zero_floor"] = "allow"

    @field_validator("component_weights")
    @classmethod
    def _weights_valid(cls, v: dict[str, Decimal]) -> dict[str, Decimal]:
        keys = set(v)
        missing = _REQUIRED_WEIGHT_KEYS - keys
        unknown = keys - _REQUIRED_WEIGHT_KEYS
        if missing or unknown:
            parts = []
            if missing:
                parts.append(f"missing: {sorted(missing)}")
            if unknown:
                parts.append(f"unknown: {sorted(unknown)}")
            raise ValueError(f"component_weights must contain exactly {sorted(_REQUIRED_WEIGHT_KEYS)} ({'; '.join(parts)})")
        for k, w in v.items():
            if w < Decimal("0"):
                raise ValueError(f"component_weights[{k}] must be >= 0")
        return v


class PVCRuleSetOut(APIModel):
    id: UUID
    contract_id: UUID
    version: int
    quarter_mode: str
    component_weights: dict[str, str]
    extra_item_policy: str
    adjustable_fraction: JsonDecimal
    rounding_mode: str
    negative_pvc_policy: str
    created_at: str


def _rule_row(r) -> dict:
    weights = r.component_weights
    if not isinstance(weights, dict):
        import json
        weights = json.loads(weights)
    return {
        "id": r.id, "contract_id": r.contract_id, "version": r.version,
        "quarter_mode": r.quarter_mode, "component_weights": {k: str(v) for k, v in weights.items()},
        "extra_item_policy": r.extra_item_policy, "adjustable_fraction": r.adjustable_fraction,
        "rounding_mode": r.rounding_mode, "negative_pvc_policy": r.negative_pvc_policy,
        "created_at": r.created_at.isoformat(),
    }


@router.get("/api/contracts/{contract_id}/pvc-rule-set", response_model=PVCRuleSetOut)
async def get_rule_set(contract_id: UUID, tenant_id: TenantDep, db: DbDep):
    await _assert_contract_tenant(db, contract_id, tenant_id)
    row = (
        await db.execute(
            text("SELECT * FROM pvc_rule_sets WHERE contract_id = :cid ORDER BY version DESC LIMIT 1"),
            {"cid": str(contract_id)},
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="No rule set found for this contract")
    return _rule_row(row)


@router.put("/api/contracts/{contract_id}/pvc-rule-set", response_model=PVCRuleSetOut)
async def upsert_rule_set(contract_id: UUID, body: PVCRuleSetIn, tenant_id: TenantDep, db: DbDep):
    await _assert_contract_tenant(db, contract_id, tenant_id)
    import json

    current = (
        await db.execute(
            text("SELECT version FROM pvc_rule_sets WHERE contract_id = :cid ORDER BY version DESC LIMIT 1"),
            {"cid": str(contract_id)},
        )
    ).one_or_none()
    new_version = (current.version + 1) if current else 1

    row = (
        await db.execute(
            text("""
                INSERT INTO pvc_rule_sets
                    (contract_id, version, quarter_mode, component_weights, extra_item_policy,
                     adjustable_fraction, rounding_mode, negative_pvc_policy)
                VALUES
                    (:cid, :ver, :qmode::quarter_mode, :weights::jsonb, :eip::extra_item_policy,
                     :adj, :rmode::rounding_mode, :npvc::negative_pvc_policy)
                RETURNING *
            """),
            {
                "cid": str(contract_id), "ver": new_version, "qmode": body.quarter_mode,
                "weights": json.dumps({k: str(v) for k, v in body.component_weights.items()}),
                "eip": body.extra_item_policy, "adj": body.adjustable_fraction,
                "rmode": body.rounding_mode, "npvc": body.negative_pvc_policy,
            },
        )
    ).one()
    await db.commit()
    return _rule_row(row)
