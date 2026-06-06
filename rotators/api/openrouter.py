"""OpenRouter API key rotator."""

from __future__ import annotations

import logging

import httpx

from rotators.api.base_api import BaseAPIRotator

log = logging.getLogger(__name__)

BASE_URL = "https://openrouter.ai/api/v1"


class Rotator(BaseAPIRotator):
    def rotate(self, current_key: str) -> str:
        with self._client(current_key, BASE_URL) as client:
            resp = client.get("/auth/keys")
            resp.raise_for_status()
            keys = resp.json().get("data", [])

            new_resp = client.post("/auth/keys", json={"name": "keymaster-rotated"})
            new_resp.raise_for_status()
            new_key = new_resp.json()["key"]

            with self._client(new_key, BASE_URL) as new_client:
                for k in keys:
                    new_client.delete(f"/auth/keys/{k['hash']}")

        log.info("openrouter: rotated successfully")
        return new_key

    def validate(self, key: str) -> tuple[bool, str]:
        try:
            resp = httpx.get(f"{BASE_URL}/auth/key", headers={"Authorization": f"Bearer {key}"}, timeout=self.TIMEOUT)
            if resp.status_code == 200:
                return True, "OK"
            return False, f"HTTP {resp.status_code}"
        except Exception as exc:
            return False, str(exc)
