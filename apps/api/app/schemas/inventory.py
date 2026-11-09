from pydantic import BaseModel, ConfigDict, Field


class StockAdjustment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    quantity: int = Field(ge=0, le=100_000)
    note: str = Field(default="", max_length=240)
