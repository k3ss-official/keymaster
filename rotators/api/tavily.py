"""Tavily API key rotator."""

from __future__ import annotations

import logging

import httpx

from rotators.api.base_api import BaseAPIRotator

log = logging.getLogger(__name__)

BASE_URL = "https://api.tavily.com"


class Rotator(BaseAPIRotator):
    def rotate(self, current_key: str) -> str:
        """Regenerate Tavily API key via the account API.

        Tavily's regenerate endpoint swaps the key in one call. There is no
        separate create-then-delete path; treat a failed vault write after
        success as a glass-break recovery case.
        """
        with httpx.Client(timeout=self.TIMEOUT) as client:
            resp = client.post(
                f"{BASE_URL}/key/regenerate",
                headers={"Authorization": f"Bearer {current_key}"},
            )
            resp.raise_for_status()
            new_key = resp.json().get("api_key")
            if not new_key:
                raise RuntimeError("Tavily regenerate response missing api_key")

        ok, msg = self.validate(new_key)
        if not ok:
            raise RuntimeError(f"Tavily new key failed validation: {msg}")

        log.info("tavily: rotated successfully")
        return new_key

    def validate(self, key: str) -> tuple[bool, str]:
        try:
            resp = httpx.post(
                f"{BASE_URL}/search",
                json={"api_key": key, "query": "ping", "max_results": 1},
                timeout=self.TIMEOUT,
            )
            if resp.status_code == 200:
                return True, "OK"
            return False, f"HTTP {resp.status_code}"
        except Exception as exc:
            return False, str(exc)
