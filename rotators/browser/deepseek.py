"""DeepSeek API key rotator — Playwright-based."""

from __future__ import annotations

import logging

from rotators.browser.base_browser import BaseBrowserRotator

log = logging.getLogger(__name__)

PORTAL_URL = "https://platform.deepseek.com/api_keys"


class Rotator(BaseBrowserRotator):
    def rotate(self, current_key: str) -> str:
        with self._browser() as pw:
            browser = pw.chromium.launch(headless=self.HEADLESS)
            page = browser.new_page()
            page.goto(PORTAL_URL)

            # Assumes user is already logged in via stored browser state
            # or that DEEPSEEK_SESSION env var is handled upstream
            page.wait_for_selector("[data-testid='api-key-list']", timeout=15_000)

            # Click the first key's delete button
            page.click("[data-testid='delete-api-key']:first-child")
            page.click("[data-testid='confirm-delete']")

            # Create new key
            page.click("[data-testid='create-api-key']")
            page.fill("[data-testid='key-name-input']", "keymaster-rotated")
            page.click("[data-testid='submit-create-key']")
            new_key = page.inner_text("[data-testid='new-key-value']")
            browser.close()

        log.info("deepseek: rotated successfully")
        return new_key.strip()
