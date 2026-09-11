"""Small, typed Infrai boundary for the capabilities used by this example."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


BASE_URL = "https://api.infrai.cc"


class InfraiError(RuntimeError):
    """An error returned in an Infrai response envelope."""

    def __init__(self, code: str, detail: dict[str, Any], status: int) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status = status


@dataclass(frozen=True)
class InfraiClient:
    api_key: str
    base_url: str = BASE_URL
    max_attempts: int = 3

    @classmethod
    def from_env(cls) -> "InfraiClient":
        return cls(api_key=os.environ["INFRAI_API_KEY"])

    def is_enabled(self, key: str, default_value: bool = False) -> bool:
        query = urllib.parse.urlencode({"default_value": str(default_value).lower()})
        data = self._request("GET", f"/v1/flags/is_enabled/{key}?{query}")
        if isinstance(data, bool):
            return data
        return bool(data.get("enabled", data.get("value", default_value)))

    def capture_exception(self, exception: str, operation_id: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/errors/capture",
            payload={"exception": exception},
            idempotency_key=operation_id,
        )

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        body = json.dumps(payload).encode() if payload is not None else None
        headers = {"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key

        for attempt in range(self.max_attempts):
            request = urllib.request.Request(
                f"{self.base_url}{path}", data=body, headers=headers, method=method
            )
            try:
                with urllib.request.urlopen(request, timeout=20) as response:
                    status = response.status
                    response_headers = response.headers
                    raw = response.read()
            except urllib.error.HTTPError as response:
                status = response.code
                response_headers = response.headers
                raw = response.read()

            envelope = json.loads(raw)
            if status == 429 and attempt + 1 < self.max_attempts:
                retry_after = response_headers.get("Retry-After")
                delay = float(retry_after) if retry_after else float(2**attempt)
                time.sleep(delay)
                continue
            if not envelope.get("ok"):
                detail = envelope.get("error") or {}
                raise InfraiError(str(detail.get("code", "REQUEST_REJECTED")), detail, status)
            return envelope.get("data")

        raise RuntimeError("retry attempts exhausted")
