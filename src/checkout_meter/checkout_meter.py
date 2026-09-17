from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Literal
from uuid import uuid5, NAMESPACE_URL


class OrderPhase(StrEnum):
    CHECKOUT = "checkout"
    FULFILLMENT = "fulfillment"
    RECEIPT = "receipt"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class OrderUpdate:
    customer_id: str
    order_id: str
    phase: OrderPhase
    api_operation: str


@dataclass(frozen=True)
class UsageReceipt:
    customer_id: str
    order_id: str
    phase: str
    api_operation: str
    billable_units: int
    decision: Literal["metered", "ignored"]
    idempotency_key: str

    def as_dict(self) -> dict[str, str | int]:
        receipt = asdict(self)
        receipt["phase"] = str(self.phase)
        return receipt


class ReceiptLedger:
    def __init__(self) -> None:
        self._receipts: dict[str, UsageReceipt] = {}

    def save(self, receipt: UsageReceipt) -> UsageReceipt:
        self._receipts.setdefault(receipt.idempotency_key, receipt)
        return self._receipts[receipt.idempotency_key]


class CheckoutMeter:
    def __init__(self, ledger: ReceiptLedger) -> None:
        self._ledger = ledger

    def record_update(self, update: OrderUpdate) -> UsageReceipt:
        key = str(uuid5(NAMESPACE_URL, f"{update.customer_id}:{update.order_id}:{update.phase}:{update.api_operation}"))
        eligible = update.phase in {OrderPhase.CHECKOUT, OrderPhase.FULFILLMENT, OrderPhase.RECEIPT}
        receipt = UsageReceipt(
            customer_id=update.customer_id,
            order_id=update.order_id,
            phase=update.phase,
            api_operation=update.api_operation,
            billable_units=1 if eligible else 0,
            decision="metered" if eligible else "ignored",
            idempotency_key=key,
        )
        return self._ledger.save(receipt)
