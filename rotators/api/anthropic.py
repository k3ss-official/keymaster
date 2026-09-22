"""Anthropic API key rotator."""

from __future__ import annotations

import logging

import httpx

from rotators.api.base_api import BaseAPIRotator

log = logging.getLogger(__name__)

BASE_URL = "https://api.anthropic.com/v1"


def _headers(api_key: str) -> dict[str, str]:
    return {"x-api-key": api_key, "anthropic-version": "2023-06-01"}


class Rotator(BaseAPIRotator):
    def rotate(self, current_key: str) -> str:
        with httpx.Client(timeout=self.TIMEOUT) as client:
            list_resp = client.get(f"{BASE_URL}/api-keys", headers=_headers(current_key))
            list_resp.raise_for_status()
            old_keys = list_resp.json().get("data", [])

            new_resp = client.post(
                f"{BASE_URL}/api-keys",
                headers=_headers(current_key),
                json={"name": "keymaster-rotated"},
            )
            new_resp.raise_for_status()
            payload = new_resp.json()
            new_key = payload.get("key") or payload.get("api_key")
            if not new_key:
                raise RuntimeError("Anthropic create-key response missing key material")
            new_id = payload.get("id")

            ok, msg = self.validate(new_key)
            if not ok:
                raise RuntimeError(f"Anthropic new key failed validation: {msg}")

            for k in old_keys:
                kid = k.get("id")
                if not kid or kid == new_id:
                    continue
                client.delete(
                    f"{BASE_URL}/api-keys/{kid}",
                    headers=_headers(new_key),
                )

        log.info("anthropic: rotated successfully")
        return new_key

    def validate(self, key: str) -> tuple[bool, str]:
        try:
            resp = httpx.get(
                f"{BASE_URL}/models",
                headers=_headers(key),
                timeout=self.TIMEOUT,
            )
            if resp.status_code == 200:
                return True, "OK"
            return False, f"HTTP {resp.status_code}"
        except Exception as exc:
            return False, str(exc)
