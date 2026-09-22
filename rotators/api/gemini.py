"""Google Gemini API key rotator (via Google Cloud API Keys API)."""

from __future__ import annotations

import logging
import os

import httpx

from rotators.api.base_api import BaseAPIRotator

log = logging.getLogger(__name__)

BASE_URL = "https://apikeys.googleapis.com/v2"


class Rotator(BaseAPIRotator):
    """
    Google API key rotation requires an OAuth2 / service-account access token
    with ``roles/serviceusage.apiKeysAdmin``. The ``current_key`` argument to
    ``rotate`` is that access token — not the Gemini browser key itself.

    ``validate`` takes the Gemini API key string and hits Generative Language.
    Set ``GOOGLE_CLOUD_PROJECT`` in the environment (also documented in
    ``.env.example``).
    """

    def rotate(self, current_key: str) -> str:
        project = os.getenv("GOOGLE_CLOUD_PROJECT", "").strip()
        if not project:
            raise RuntimeError(
                "GOOGLE_CLOUD_PROJECT is required for Gemini key rotation"
            )

        headers = {"Authorization": f"Bearer {current_key}"}
        parent = f"projects/{project}/locations/global"

        with httpx.Client(timeout=self.TIMEOUT) as client:
            resp = client.get(f"{BASE_URL}/{parent}/keys", headers=headers)
            resp.raise_for_status()
            old_keys = resp.json().get("keys", [])

            new_resp = client.post(
                f"{BASE_URL}/{parent}/keys",
                headers=headers,
                json={"displayName": "keymaster-rotated"},
            )
            new_resp.raise_for_status()
            new_payload = new_resp.json()
            new_key = new_payload.get("keyString")
            new_name = new_payload.get("name")
            if not new_key:
                raise RuntimeError("Gemini create-key response missing keyString")

            ok, msg = self.validate(new_key)
            if not ok:
                raise RuntimeError(f"Gemini new key failed validation: {msg}")

            for k in old_keys:
                name = k.get("name")
                if not name or name == new_name:
                    continue
                client.delete(f"{BASE_URL}/{name}", headers=headers)

        log.info("gemini: rotated successfully")
        return new_key

    def validate(self, key: str) -> tuple[bool, str]:
        try:
            resp = httpx.get(
                "https://generativelanguage.googleapis.com/v1beta/models",
                params={"key": key},
                timeout=self.TIMEOUT,
            )
            if resp.status_code == 200:
                return True, "OK"
            return False, f"HTTP {resp.status_code}"
        except Exception as exc:
            return False, str(exc)
