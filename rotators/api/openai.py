"""OpenAI API key rotator."""

from __future__ import annotations

import logging

import httpx

from rotators.api.base_api import BaseAPIRotator

log = logging.getLogger(__name__)

BASE_URL = "https://api.openai.com/v1"


class Rotator(BaseAPIRotator):
    def rotate(self, current_key: str) -> str:
        with self._client(current_key, BASE_URL) as client:
            # List existing API keys
            resp = client.get("/organization/api_keys")
            resp.raise_for_status()
            keys = resp.json().get("data", [])

            # Create new key
            new_resp = client.post("/organization/api_keys", json={"name": "keymaster-rotated"})
            new_resp.raise_for_status()
            new_key_data = new_resp.json()
            new_key = new_key_data["sensitive_id"]

            # Delete old keys
            with self._client(new_key, BASE_URL) as new_client:
                for k in keys:
                    new_client.delete(f"/organization/api_keys/{k['id']}")

        log.info("openai: rotated successfully")
        return new_key

    def validate(self, key: str) -> tuple[bool, str]:
        try:
            resp = httpx.get(f"{BASE_URL}/models", headers={"Authorization": f"Bearer {key}"}, timeout=self.TIMEOUT)
            if resp.status_code == 200:
                return True, "OK"
            return False, f"HTTP {resp.status_code}"
        except Exception as exc:
            return False, str(exc)
