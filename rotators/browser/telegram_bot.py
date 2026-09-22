"""Telegram Bot token rotator — regenerates via BotFather."""

from __future__ import annotations

import logging
import os
import re

from rotators.browser.base_browser import BaseBrowserRotator

log = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"\d+:[A-Za-z0-9_-]{35,}")


class Rotator(BaseBrowserRotator):
    """Uses Playwright to chat with @BotFather and issue /token for the bot."""

    BOTFATHER_URL = "https://web.telegram.org/k/#@BotFather"
    BOT_NAME = os.getenv("KEYMASTER_TELEGRAM_BOT_NAME", "Rae_plex_bot")

    def rotate(self, current_key: str) -> str:
        """
        Requires Telegram Web already logged in on the MBP Chromium profile.
        Regenerating the bot token via BotFather invalidates ``current_key``
        immediately — vault write + glass-break must succeed afterwards.
        """
        with self._browser() as pw:
            browser = pw.chromium.launch(headless=self.HEADLESS)
            try:
                page = browser.new_page()
                page.goto(self.BOTFATHER_URL)
                page.wait_for_selector(".input-message-input", timeout=20_000)

                page.fill(".input-message-input", "/token")
                page.keyboard.press("Enter")

                page.wait_for_selector(f"text={self.BOT_NAME}", timeout=10_000)
                page.click(f"text={self.BOT_NAME}")

                page.wait_for_selector(".message.out + .message", timeout=15_000)
                reply = page.inner_text(".message.out + .message")
            finally:
                browser.close()

        match = _TOKEN_RE.search(reply)
        if not match:
            raise ValueError(f"Could not extract token from BotFather reply: {reply!r}")
        new_token = match.group(0)
        log.info("telegram_bot: rotated successfully")
        return new_token
