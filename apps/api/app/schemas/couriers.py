from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ShipmentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    courier_name: str = Field(min_length=1, max_length=100)
    awb: str = Field(min_length=1, max_length=100)
    tracking_url: HttpUrl | None = None
    courier_connection_id: int | None = None


class ShipmentStatusIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["label_created", "picked_up", "in_transit", "out_for_delivery", "delivered", "exception", "returned"]
    detail: str = Field(default="", max_length=300)


class CourierConnectionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)
    provider: str = Field(default="generic", min_length=1, max_length=40)
    credentials: dict[str, str] = Field(default_factory=dict)


class CourierWebhookIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: str = Field(min_length=1, max_length=160)
    awb: str = Field(default="", max_length=100)
    order_code: str = Field(default="", max_length=32)
    status: str = Field(min_length=1, max_length=64)
    detail: str = Field(default="", max_length=300)
