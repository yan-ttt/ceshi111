from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import urlencode
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx


@dataclass
class GateCredentials:
    api_key: str
    api_secret: str
    api_host: str


class GateAPI:
    def __init__(self, credentials: GateCredentials, max_retries: int = 3, retry_backoff_s: float = 0.5) -> None:
        self.credentials = credentials
        self.client = httpx.Client(base_url=credentials.api_host, timeout=10.0)
        self.max_retries = max_retries
        self.retry_backoff_s = retry_backoff_s

    def _sign(self, method: str, path: str, query: str, body: str) -> Dict[str, str]:
        timestamp = str(int(time.time()))
        payload = f"{method}\n{path}\n{query}\n{body}\n{timestamp}"
        signature = hmac.new(
            self.credentials.api_secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha512,
        ).hexdigest()
        return {
            "KEY": self.credentials.api_key,
            "Timestamp": timestamp,
            "SIGN": signature,
        }

    def request(
        self,
        method: str,
        path: str,
        json_body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        body = "" if json_body is None else json.dumps(json_body, separators=(",", ":"))
        query = "" if not params else urlencode(params, doseq=True)
        headers = self._sign(method, path, query, body)
        return self._send_with_retry(method, path, headers=headers, json=json_body, params=params)

    def public_request(self, method: str, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self._send_with_retry(method, path, params=params)

    def _send_with_retry(
        self,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        for attempt in range(1, self.max_retries + 1):
            response = self.client.request(method, path, headers=headers, json=json, params=params)
            if response.status_code < 500:
                response.raise_for_status()
                return response.json()
            if attempt < self.max_retries:
                time.sleep(self.retry_backoff_s * attempt)
        response.raise_for_status()
        return response.json()

    def fetch_spot_candles(self, symbol: str, interval: str, limit: int) -> Any:
        params = {"currency_pair": symbol, "interval": interval, "limit": str(limit)}
        return self.public_request("GET", "/api/v4/spot/candlesticks", params=params)

    def place_spot_order(self, symbol: str, side: str, amount: float, price: Optional[float] = None) -> Dict[str, Any]:
        data = {
            "currency_pair": symbol,
            "side": side,
            "amount": str(amount),
            "type": "market" if price is None else "limit",
        }
        if price is not None:
            data["price"] = str(price)
        return self.request("POST", "/api/v4/spot/orders", data)

    def get_spot_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        path = f"/api/v4/spot/orders/{order_id}"
        return self.request("GET", path, params={"currency_pair": symbol})

    def list_spot_balances(self) -> Any:
        return self.request("GET", "/api/v4/spot/accounts")

    def place_futures_order(
        self,
        contract: str,
        side: str,
        size: float,
        leverage: int = 5,
    ) -> Dict[str, Any]:
        data = {
            "contract": contract,
            "size": str(size),
            "price": "0",
            "tif": "ioc",
            "auto_size": side,
            "leverage": str(leverage),
        }
        return self.request("POST", "/api/v4/futures/usdt/orders", data)

    def list_futures_positions(self) -> Any:
        return self.request("GET", "/api/v4/futures/usdt/positions")

    def get_futures_order(self, order_id: str) -> Dict[str, Any]:
        path = f"/api/v4/futures/usdt/orders/{order_id}"
        return self.request("GET", path)
