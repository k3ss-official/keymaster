"""Base class for API-based key rotators."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

import httpx

log = logging.getLogger(__name__)


class BaseAPIRotator(ABC):
    """Rotate a key via the provider's REST management API."""

    TIMEOUT = 30.0

    # ------------------------------------------------------------------ #
    #  Subclasses must implement                                            #
    # ------------------------------------------------------------------ #

    @abstractmethod
    def rotate(self, current_key: str) -> str:
        """Delete the old key, create a new one, return the new key."""
        ...

    @abstractmethod
    def validate(self, key: str) -> tuple[bool, str]:
        """Return (ok, message) for *key*."""
        ...

    # ------------------------------------------------------------------ #
    #  Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _client(self, api_key: str, base_url: str) -> httpx.Client:
        return httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=self.TIMEOUT,
        )
