"""GitHub PAT rotator — deletes old fine-grained PAT and creates a new one."""

from __future__ import annotations

import datetime
import logging

import httpx

from rotators.api.base_api import BaseAPIRotator

log = logging.getLogger(__name__)

BASE_URL = "https://api.github.com"


class Rotator(BaseAPIRotator):
    def rotate(self, current_key: str) -> str:
        headers = {
            "Authorization": f"Bearer {current_key}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        with httpx.Client(timeout=self.TIMEOUT) as client:
            # List fine-grained PATs
            resp = client.get(f"{BASE_URL}/user/personal-access-tokens", headers=headers)
            resp.raise_for_status()
            tokens = resp.json()

            # Create new PAT
            expiry = (datetime.date.today() + datetime.timedelta(days=90)).isoformat()
            new_resp = client.post(
                f"{BASE_URL}/user/personal-access-tokens",
                headers=headers,
                json={
                    "name": "keymaster-rotated",
                    "expiration_date": expiry,
                    "permissions": {},
                },
            )
            new_resp.raise_for_status()
            new_token = new_resp.json()["token"]

            # Delete old tokens
            new_headers = {**headers, "Authorization": f"Bearer {new_token}"}
            for tok in tokens:
                client.delete(
                    f"{BASE_URL}/user/personal-access-tokens/{tok['id']}",
                    headers=new_headers,
                )

        log.info("github_pat: rotated successfully")
        return new_token

    def validate(self, key: str) -> tuple[bool, str]:
        try:
            resp = httpx.get(
                f"{BASE_URL}/user",
                headers={"Authorization": f"Bearer {key}", "Accept": "application/vnd.github+json"},
                timeout=self.TIMEOUT,
            )
            if resp.status_code == 200:
                return True, "OK"
            return False, f"HTTP {resp.status_code}"
        except Exception as exc:
            return False, str(exc)
