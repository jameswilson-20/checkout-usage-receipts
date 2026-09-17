from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from .checkout_meter import CheckoutMeter, OrderPhase, OrderUpdate


def order_update_app(meter: CheckoutMeter) -> Callable[[dict[str, Any], Callable[..., Any]], list[bytes]]:
    def app(environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        if environ.get("REQUEST_METHOD") != "POST" or environ.get("PATH_INFO") != "/order-updates":
            start_response("404 Not Found", [("Content-Type", "application/json")])
            return [b'{"error":"route_not_found"}']
        length = int(environ.get("CONTENT_LENGTH") or 0)
        body = json.loads(environ["wsgi.input"].read(length))
        update = OrderUpdate(
            customer_id=body["customer_id"],
            order_id=body["order_id"],
            phase=OrderPhase(body["phase"]),
            api_operation=body["api_operation"],
        )
        receipt = meter.record_update(update)
        encoded = json.dumps(receipt.as_dict()).encode("utf-8")
        start_response("201 Created", [("Content-Type", "application/json"), ("Content-Length", str(len(encoded)))])
        return [encoded]

    return app
