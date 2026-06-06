"""Base class for Playwright-based rotators."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

log = logging.getLogger(__name__)


class BaseBrowserRotator(ABC):
    """Launch a headless Chromium session and interact with the provider UI."""

    HEADLESS = True

    @abstractmethod
    def rotate(self, current_key: str) -> str:
        """Return the new API key after rotation."""
        ...

    def validate(self, key: str) -> tuple[bool, str]:
        """Browser rotators validate by attempting rotation — override if cheaper check exists."""
        return True, "browser-rotator: validate not implemented"

    def _browser(self):
        """Return a configured Playwright browser context manager."""
        from playwright.sync_api import sync_playwright
        return sync_playwright()
