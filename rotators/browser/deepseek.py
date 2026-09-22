"""DeepSeek API key rotator — Playwright-based."""

from __future__ import annotations

import logging

import httpx

from rotators.browser.base_browser import BaseBrowserRotator

log = logging.getLogger(__name__)

PORTAL_URL = "https://platform.deepseek.com/api_keys"
VALIDATE_URL = "https://api.deepseek.com/models"


class Rotator(BaseBrowserRotator):
    def rotate(self, current_key: str) -> str:
        """
        Requires an already-authenticated Chromium profile / session cookies
        on the MBP (Janet). Without a logged-in session this will time out.
        """
        with self._browser() as pw:
            browser = pw.chromium.launch(headless=self.HEADLESS)
            try:
                page = browser.new_page()
                page.goto(PORTAL_URL)
                page.wait_for_selector("[data-testid='api-key-list']", timeout=15_000)

                page.click("[data-testid='delete-api-key']:first-child")
                page.click("[data-testid='confirm-delete']")

                page.click("[data-testid='create-api-key']")
                page.fill("[data-testid='key-name-input']", "keymaster-rotated")
                page.click("[data-testid='submit-create-key']")
                new_key = page.inner_text("[data-testid='new-key-value']")
            finally:
                browser.close()

        new_key = new_key.strip()
        ok, msg = self.validate(new_key)
        if not ok:
            raise RuntimeError(f"DeepSeek new key failed validation: {msg}")

        log.info("deepseek: rotated successfully")
        return new_key

    def validate(self, key: str) -> tuple[bool, str]:
        if not key:
            return False, "empty key"
        try:
            resp = httpx.get(
                VALIDATE_URL,
                headers={"Authorization": f"Bearer {key}"},
                timeout=30.0,
            )
            if resp.status_code == 200:
                return True, "OK"
            return False, f"HTTP {resp.status_code}"
        except Exception as exc:
            return False, str(exc)
