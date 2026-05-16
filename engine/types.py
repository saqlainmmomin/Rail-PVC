from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator


class ExtraItemDecision(BaseModel):
    item_id: str
    amount: Decimal
    eligible: bool | None = None  # None = undecided; blocks run


class CarryForwardPayload(BaseModel):
    """Steel carry-forward from a prior bill.

    Inputs are deliberately minimal — `paid_ratio` and `carry_qty` are derived,
    so the model cannot represent contradictory state (e.g., ratio > 1 or
    carry_qty < 0).
    """
    item_id: str
    recorded_qty: Decimal = Field(gt=Decimal("0"))
    paid_qty_source: Decimal = Field(ge=Decimal("0"))
    amount: Decimal = Field(ge=Decimal("0"))
    steel_subtype: Literal["angles", "plates", "other_sections", "tmt"] | None = None

    @model_validator(mode="after")
    def _paid_qty_within_recorded(self) -> "CarryForwardPayload":
        if self.paid_qty_source > self.recorded_qty:
            raise ValueError(
                f"paid_qty_source ({self.paid_qty_source}) cannot exceed "
                f"recorded_qty ({self.recorded_qty})"
            )
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def paid_ratio(self) -> Decimal:
        return self.paid_qty_source / self.recorded_qty

    @computed_field  # type: ignore[prop-decorator]
    @property
    def carry_qty(self) -> Decimal:
        return self.recorded_qty - self.paid_qty_source


class BillPayload(BaseModel):
    on_account_amount: Decimal
    cement_amount: Decimal
    steel_angles_amount: Decimal
    steel_plates_amount: Decimal
    steel_tmt_amount: Decimal                   # GCC 46A.9 SL1 — TMT/rebar items (required; zero must be explicit)
    steel_other_amount: Decimal                 # GCC 46A.9 SL4 — other sections
    technical_withheld: Decimal
    extra_item_decisions: list[ExtraItemDecision]  # P2-004: eligible=None blocks run
    carry_forwards: list[CarryForwardPayload]
    measurement_date: date  # must be the "To" date of the measurement period
    prior_negative_carry_forward: Decimal = Decimal("0")  # recovery from previous bill


class IndexSnapshot(BaseModel):
    base_month: date
    series: dict[str, dict[str, Decimal]]  # {series_name: {"YYYY-MM": value}}


REQUIRED_GENERAL_WEIGHTS: frozenset[str] = frozenset(
    {"labour", "plant", "fuel", "materials"}
)


class PVCRuleSet(BaseModel):
    # Only measurement_date is a valid quarter anchor (KU-001). The historical
    # "bill_date" mode never existed; rejecting it at the schema level
    # prevents silent miscomputation downstream.
    quarter_mode: Literal["measurement_date"]
    component_weights: dict[str, Decimal]
    adjustable_fraction: Decimal           # typically 0.85
    negative_pvc_policy: Literal["allow", "block", "zero_floor"]
    rounding_mode: Literal["round_2", "truncate_2"]

    @field_validator("component_weights")
    @classmethod
    def _weights_complete_and_known(cls, v: dict[str, Decimal]) -> dict[str, Decimal]:
        keys = set(v)
        missing = REQUIRED_GENERAL_WEIGHTS - keys
        unknown = keys - REQUIRED_GENERAL_WEIGHTS
        if missing or unknown:
            parts = []
            if missing:
                parts.append(f"missing keys: {sorted(missing)}")
            if unknown:
                parts.append(f"unknown keys: {sorted(unknown)}")
            raise ValueError(
                "component_weights must contain exactly "
                f"{sorted(REQUIRED_GENERAL_WEIGHTS)} ({'; '.join(parts)})"
            )
        for k, w in v.items():
            if w < Decimal("0"):
                raise ValueError(f"component_weights[{k}] must be >= 0, got {w}")
        return v


class WDerivation(BaseModel):
    on_account_amount: Decimal
    cement: Decimal
    steel_angles: Decimal
    steel_plates: Decimal
    steel_tmt: Decimal      # GCC 46A.9 SL1 — TMT/rebar items
    steel_other: Decimal    # GCC 46A.9 SL4 — other sections
    technical_withheld: Decimal
    extra_items: Decimal  # sum of excluded (eligible=False) extra item amounts
    w: Decimal


class PVCComponent(BaseModel):
    category: str
    eligible_amount: Decimal
    base_index: Decimal
    current_avg_index: Decimal
    weight: Decimal
    pvc_value: Decimal


class PVCRunResult(BaseModel):
    w: Decimal | None
    w_derivation: WDerivation | None
    components: list[PVCComponent]
    total_pvc: Decimal | None
    negative_carry_forward: Decimal  # amount to recover from next bill (zero_floor policy)
    quarter_used: str | None
    quarter_months: list[str]
    trace: dict
    validation_errors: list[str]
