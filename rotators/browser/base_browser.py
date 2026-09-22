"""Base class for Playwright-based rotators."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Iterator

log = logging.getLogger(__name__)


class BaseBrowserRotator(ABC):
    """Launch a headless Chromium session and interact with the provider UI."""

    HEADLESS = True

    @abstractmethod
    def rotate(self, current_key: str) -> str:
        """Return the new API key after rotation."""
        ...

    def validate(self, key: str) -> tuple[bool, str]:
        """Cheap validate is provider-specific; default is a no-op pass.

        Browser portals rarely expose a key-check endpoint. Override when a
        lightweight API ping exists (e.g. DeepSeek chat completions).
        """
        if not key:
            return False, "empty key"
        return True, "browser-rotator: validate skipped (no cheap check)"

    @contextmanager
    def _browser(self) -> Iterator:
        """Yield a Playwright instance; caller must close browsers/pages."""
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            yield pw
