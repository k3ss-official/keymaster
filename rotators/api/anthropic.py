"""Anthropic API key rotator."""

from __future__ import annotations

import logging

import httpx

from rotators.api.base_api import BaseAPIRotator

log = logging.getLogger(__name__)

BASE_URL = "https://api.anthropic.com/v1"


class Rotator(BaseAPIRotator):
    def rotate(self, current_key: str) -> str:
        with httpx.Client(timeout=self.TIMEOUT) as client:
            # List existing keys
            resp = client.get(
                f"{BASE_URL}/api-keys",
                headers={"x-api-key": current_key, "anthropic-version": "2023-06-01"},
            )
            resp.raise_for_status()
            keys = resp.json().get("data", [])

            # Create new key
            new_resp = client.post(
                f"{BASE_URL}/api-keys",
                headers={"x-api-key": current_key, "anthropic-version": "2023-06-01"},
                json={"name": "keymaster-rotated"},
            )
            new_resp.raise_for_status()
            new_key = new_resp.json()["key"]

            # Delete old keys (except the new one)
            for k in keys:
                if k["key"] != new_key:
                    client.delete(
                        f"{BASE_URL}/api-keys/{k['id']}",
                        headers={"x-api-key": new_key, "anthropic-version": "2023-06-01"},
                    )

        log.info("anthropic: rotated successfully")
        return new_key

    def validate(self, key: str) -> tuple[bool, str]:
        try:
            resp = httpx.get(
                f"{BASE_URL}/models",
                headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
                timeout=self.TIMEOUT,
            )
            if resp.status_code == 200:
                return True, "OK"
            return False, f"HTTP {resp.status_code}"
        except Exception as exc:
            return False, str(exc)
