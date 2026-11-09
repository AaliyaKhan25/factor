"""Courier adapter contract and status normalization. No provider is required to ship an order."""
from typing import Protocol


STATUS_ALIASES = {
    "created": "label_created", "label created": "label_created", "manifested": "label_created",
    "picked up": "picked_up", "picked_up": "picked_up", "pickup complete": "picked_up",
    "in transit": "in_transit", "in_transit": "in_transit", "shipped": "in_transit", "dispatched": "in_transit",
    "out for delivery": "out_for_delivery", "out_for_delivery": "out_for_delivery", "ofd": "out_for_delivery",
    "delivered": "delivered", "delivery complete": "delivered",
    "exception": "exception", "failed": "exception", "delivery failed": "exception", "undelivered": "exception",
    "returned": "returned", "rto": "returned", "return to origin": "returned",
}


def normalize_status(value: str) -> str:
    key = " ".join(value.strip().lower().replace("-", " ").split())
    normalized = STATUS_ALIASES.get(key)
    if not normalized:
        raise ValueError(f"Unsupported courier status: {value}")
    return normalized


class CourierAdapter(Protocol):
    def poll(self, credentials: dict[str, str], awb: str) -> str | None: ...


class GenericAdapter:
    """Provider hook for a future seller-specific API implementation."""
    def poll(self, credentials: dict[str, str], awb: str) -> str | None:
        return None


class FakeCourierAdapter:
    """Deterministic adapter used in tests and local integration setup."""
    def poll(self, credentials: dict[str, str], awb: str) -> str | None:
        status = credentials.get("next_status")
        if not status:
            return None
        return normalize_status(status)


def adapter_for(provider: str) -> CourierAdapter:
    if provider.lower() == "fake":
        return FakeCourierAdapter()
    return GenericAdapter()
