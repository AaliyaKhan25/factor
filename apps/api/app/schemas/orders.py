"""Order schemas. The client never sends a price: the server takes it from the catalog."""
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CustomerIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    phone: str | None = Field(default=None, max_length=20)
    handle: str | None = Field(default=None, max_length=80)

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str | None) -> str | None:
        if v is None or not v.strip():
            return None
        digits = re.sub(r"\D", "", v)
        if len(digits) < 10:
            raise ValueError("Phone number needs at least 10 digits")
        return digits[-10:]


class LineIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    catalog_item_id: int
    quantity: int = Field(ge=1, le=1000)


class OrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    customer: CustomerIn
    source: Literal["instagram", "whatsapp", "manual"] = "manual"
    items: list[LineIn] = Field(min_length=1, max_length=50)
    note: str = Field(default="", max_length=500)


class StatusChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["confirmed", "packed", "shipped", "delivered", "cancelled"]
