"""Catalog schemas. Prices are whole paise (Rs 8.50 = 850 paise) so there is no rounding drift."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CatalogCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=160)
    kind: Literal["ready_stock", "made_to_order"]
    price_paise: int = Field(ge=0, le=100_000_000)
    quantity: int | None = Field(default=None, ge=0, le=100_000)
    capacity: int | None = Field(default=None, ge=1, le=100_000)
    lead_time_days: int | None = Field(default=None, ge=0, le=365)

    @model_validator(mode="after")
    def _fields_match_kind(self):
        if self.kind == "ready_stock":
            if self.quantity is None:
                raise ValueError("Ready stock items need a quantity")
            if self.capacity is not None:
                raise ValueError("Capacity is only for made-to-order items")
        else:
            if self.capacity is None:
                raise ValueError("Made-to-order items need a capacity")
            if self.quantity is not None:
                raise ValueError("Quantity is only for ready stock items")
        return self


class CatalogUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=160)
    price_paise: int | None = Field(default=None, ge=0, le=100_000_000)
    quantity: int | None = Field(default=None, ge=0, le=100_000)
    capacity: int | None = Field(default=None, ge=1, le=100_000)
    lead_time_days: int | None = Field(default=None, ge=0, le=365)
    active: bool | None = None
