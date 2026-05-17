"""Shared Pydantic types and helpers for Phase 3 API responses."""
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, PlainSerializer

# Serialize Decimal as string in JSON to prevent float precision loss (REVIEW HIGH-10).
JsonDecimal = Annotated[Decimal, PlainSerializer(str, return_type=str, when_used="json")]


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
