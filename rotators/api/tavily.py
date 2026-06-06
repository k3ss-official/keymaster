"""Tavily API key rotator."""

from __future__ import annotations

import logging

import httpx

from rotators.api.base_api import BaseAPIRotator

log = logging.getLogger(__name__)

BASE_URL = "https://api.tavily.com"


class Rotator(BaseAPIRotator):
    def rotate(self, current_key: str) -> str:
        """Regenerate Tavily API key via the account API."""
        with httpx.Client(timeout=self.TIMEOUT) as client:
            resp = client.post(
                f"{BASE_URL}/key/regenerate",
                headers={"Authorization": f"Bearer {current_key}"},
            )
            resp.raise_for_status()
            new_key = resp.json()["api_key"]
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
