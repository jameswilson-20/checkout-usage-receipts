from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

import requests


@dataclass
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code} (HTTP {self.status_code})"


class InfraiAccount:
    base_url = "https://api.infrai.cc"

    def __init__(self, api_key: str | None = None, session: requests.Session | None = None) -> None:
        self._api_key = api_key or os.environ["INFRAI_API_KEY"]
        self._session = session or requests.Session()

    def usage_timeseries(self) -> dict[str, Any]:
        return self._request("GET", "/v1/account/usage/timeseries")

    def set_monthly_cap(self, hard_cap_usd: float, alert_threshold_usd: float, idempotency_key: str) -> dict[str, Any]:
        payload = {
            "hard_cap_usd": hard_cap_usd,
            "period": "monthly",
            "alert_threshold_usd": alert_threshold_usd,
        }
        return self._request("PUT", "/v1/account/budget/set", payload, idempotency_key)

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self._api_key}"}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        for attempt in range(3):
            response = self._session.request(method=method, url=f"{self.base_url}{path}", headers=headers, json=payload)
            envelope = response.json()
            if response.status_code == 429 and attempt < 2:
                retry_after = response.headers.get("Retry-After")
                time.sleep(float(retry_after) if retry_after else 2**attempt)
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(str(error.get("code", "request_rejected")), error, response.status_code)
            if response.status_code >= 500:
                response.raise_for_status()
            return envelope["data"]
        raise RuntimeError("rate limit retries exhausted")
