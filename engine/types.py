from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class CarryForwardPayload(BaseModel):
    item_id: str
    recorded_qty: Decimal
    paid_qty_source: Decimal
    paid_ratio: Decimal
    carry_qty: Decimal
    steel_subtype: Literal["angles", "plates", "other_sections", "tmt"] | None = None


class BillPayload(BaseModel):
    on_account_amount: Decimal
    cement_amount: Decimal
    steel_angles_amount: Decimal
    steel_plates_amount: Decimal
    steel_other_amount: Decimal
    technical_withheld: Decimal
    extra_item_amount: Decimal  # sum of non-eligible extra items; 0 if all eligible
    carry_forwards: list[CarryForwardPayload]
    measurement_date: date


class IndexSnapshot(BaseModel):
    base_month: date
    series: dict[str, dict[str, Decimal]]  # {category: {"YYYY-MM": value}}


class PVCRuleSet(BaseModel):
    quarter_mode: Literal["measurement_date", "bill_date"]
    component_weights: dict[str, Decimal]
    adjustable_fraction: Decimal
    negative_pvc_policy: Literal["allow", "block", "zero_floor"]
    rounding_mode: Literal["round_2", "truncate_2"]


class WDerivation(BaseModel):
    on_account_amount: Decimal
    cement: Decimal
    steel_angles: Decimal
    steel_plates: Decimal
    steel_other: Decimal
    technical_withheld: Decimal
    extra_items: Decimal
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
    quarter_used: str | None
    quarter_months: list[str]
    trace: dict
    validation_errors: list[str]
