"""Base class for API-based key rotators."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

import httpx

log = logging.getLogger(__name__)


class BaseAPIRotator(ABC):
    """Rotate a key via the provider's REST management API.

    Contract for subclasses
    -----------------------
    ``rotate`` should prefer this order when the provider allows it:

    1. Create a new credential while the current key is still valid
    2. Validate the new credential
    3. Revoke / delete the old credential(s)
    4. Return the new secret

    That keeps rotations closer to idempotent: if a later vault write fails,
    the new key still exists and can be recovered from glass-break or the
    provider console.
    """

    TIMEOUT = 30.0

    @abstractmethod
    def rotate(self, current_key: str) -> str:
        """Create a new key, revoke the old one when safe, return the new key."""
        ...

    @abstractmethod
    def validate(self, key: str) -> tuple[bool, str]:
        """Return ``(ok, message)`` for *key* without mutating credentials."""
        ...

    def _client(self, api_key: str, base_url: str) -> httpx.Client:
        return httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=self.TIMEOUT,
        )
