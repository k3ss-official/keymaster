"""Google Gemini API key rotator (via Google AI Studio / Cloud API keys)."""

from __future__ import annotations

import logging

import httpx

from rotators.api.base_api import BaseAPIRotator

log = logging.getLogger(__name__)

# Google Cloud REST API for API keys
BASE_URL = "https://apikeys.googleapis.com/v2"


class Rotator(BaseAPIRotator):
    """
    NOTE: Google API key rotation requires a service-account token with
    roles/serviceusage.apiKeysAdmin.  The `current_key` passed in is
    an OAuth2 access token, not the Gemini key itself.
    """

    def rotate(self, current_key: str) -> str:
        headers = {"Authorization": f"Bearer {current_key}"}
        with httpx.Client(timeout=self.TIMEOUT) as client:
            # Assumes project is stored in env; simplified for clarity
            import os
            project = os.getenv("GOOGLE_CLOUD_PROJECT", "")
            parent = f"projects/{project}/locations/global"

            resp = client.get(f"{BASE_URL}/{parent}/keys", headers=headers)
            resp.raise_for_status()
            keys = resp.json().get("keys", [])

            new_resp = client.post(
                f"{BASE_URL}/{parent}/keys",
                headers=headers,
                json={"displayName": "keymaster-rotated"},
            )
            new_resp.raise_for_status()
            new_key = new_resp.json()["keyString"]

            for k in keys:
                client.delete(f"{BASE_URL}/{k['name']}", headers=headers)

        log.info("gemini: rotated successfully")
        return new_key

    def validate(self, key: str) -> tuple[bool, str]:
        try:
            resp = httpx.get(
                f"https://generativelanguage.googleapis.com/v1beta/models?key={key}",
                timeout=self.TIMEOUT,
            )
            if resp.status_code == 200:
                return True, "OK"
            return False, f"HTTP {resp.status_code}"
        except Exception as exc:
            return False, str(exc)
