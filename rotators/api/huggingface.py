"""HuggingFace token rotator."""

from __future__ import annotations

import logging

import httpx

from rotators.api.base_api import BaseAPIRotator

log = logging.getLogger(__name__)

BASE_URL = "https://huggingface.co/api"


class Rotator(BaseAPIRotator):
    def rotate(self, current_key: str) -> str:
        headers = {"Authorization": f"Bearer {current_key}"}
        with httpx.Client(timeout=self.TIMEOUT) as client:
            resp = client.get(f"{BASE_URL}/whoami-v2", headers=headers)
            resp.raise_for_status()
            username = resp.json()["name"]

            # List tokens
            tokens_resp = client.get(f"{BASE_URL}/user-tokens?username={username}", headers=headers)
            tokens_resp.raise_for_status()
            tokens = tokens_resp.json()

            # Create new token
            new_resp = client.post(
                f"{BASE_URL}/user-tokens?username={username}",
                headers=headers,
                json={"name": "keymaster-rotated", "type": "write"},
            )
            new_resp.raise_for_status()
            new_token = new_resp.json()["accessToken"]

            # Delete old tokens
            new_headers = {"Authorization": f"Bearer {new_token}"}
            for tok in tokens:
                client.delete(
                    f"{BASE_URL}/user-tokens?username={username}&name={tok['name']}",
                    headers=new_headers,
                )

        log.info("huggingface: rotated successfully")
        return new_token

    def validate(self, key: str) -> tuple[bool, str]:
        try:
            resp = httpx.get(f"{BASE_URL}/whoami-v2", headers={"Authorization": f"Bearer {key}"}, timeout=self.TIMEOUT)
            if resp.status_code == 200:
                return True, "OK"
            return False, f"HTTP {resp.status_code}"
        except Exception as exc:
            return False, str(exc)
