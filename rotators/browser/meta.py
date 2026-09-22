"""Meta AI / Llama API key rotator — Playwright-based."""

from __future__ import annotations

import logging

from rotators.browser.base_browser import BaseBrowserRotator

log = logging.getLogger(__name__)

PORTAL_URL = "https://www.llama.com/llama-api/"


class Rotator(BaseBrowserRotator):
    def rotate(self, current_key: str) -> str:
        """
        Requires an already-authenticated Chromium session on the MBP (Janet).
        Portal selectors are brittle — verify on hardware before enabling launchd.
        """
        with self._browser() as pw:
            browser = pw.chromium.launch(headless=self.HEADLESS)
            try:
                page = browser.new_page()
                page.goto(PORTAL_URL)
                page.wait_for_selector("[aria-label='API Keys']", timeout=15_000)

                page.click("[data-testid='revoke-key']:first-child")
                page.click("[data-testid='confirm-revoke']")

                page.click("[data-testid='generate-api-key']")
                new_key = page.inner_text("[data-testid='new-key-display']")
            finally:
                browser.close()

        new_key = new_key.strip()
        if not new_key:
            raise RuntimeError("Meta portal returned empty key material")

        log.info("meta: rotated successfully")
        return new_key
