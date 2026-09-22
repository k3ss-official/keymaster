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
            resp = client.get("/organization/api_keys")
            resp.raise_for_status()
            old_keys = resp.json().get("data", [])

            new_resp = client.post(
                "/organization/api_keys",
                json={"name": "keymaster-rotated"},
            )
            new_resp.raise_for_status()
            new_key_data = new_resp.json()
            new_key = new_key_data.get("sensitive_id") or new_key_data.get("key")
            new_id = new_key_data.get("id")
            if not new_key:
                raise RuntimeError("OpenAI create-key response missing key material")

            ok, msg = self.validate(new_key)
            if not ok:
                raise RuntimeError(f"OpenAI new key failed validation: {msg}")

            with self._client(new_key, BASE_URL) as new_client:
                for k in old_keys:
                    kid = k.get("id")
                    if not kid or kid == new_id:
                        continue
                    new_client.delete(f"/organization/api_keys/{kid}")

        log.info("openai: rotated successfully")
        return new_key

    def validate(self, key: str) -> tuple[bool, str]:
        try:
            resp = httpx.get(
                f"{BASE_URL}/models",
                headers={"Authorization": f"Bearer {key}"},
                timeout=self.TIMEOUT,
            )
            if resp.status_code == 200:
                return True, "OK"
            return False, f"HTTP {resp.status_code}"
        except Exception as exc:
            return False, str(exc)
