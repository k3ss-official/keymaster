"""Telegram Bot token rotator — regenerates via BotFather."""

from __future__ import annotations

import logging
import os

from rotators.browser.base_browser import BaseBrowserRotator

log = logging.getLogger(__name__)


class Rotator(BaseBrowserRotator):
    """Uses Playwright to chat with @BotFather and issue /token for the bot."""

    BOTFATHER_URL = "https://web.telegram.org/k/#@BotFather"
    BOT_NAME = os.getenv("KEYMASTER_TELEGRAM_BOT_NAME", "Rae_plex_bot")

    def rotate(self, current_key: str) -> str:
        with self._browser() as pw:
            browser = pw.chromium.launch(headless=self.HEADLESS)
            page = browser.new_page()
            page.goto(self.BOTFATHER_URL)
            page.wait_for_selector(".input-message-input", timeout=20_000)

            # Send /token command
            page.fill(".input-message-input", f"/token")
            page.keyboard.press("Enter")

            # Select bot
            page.wait_for_selector(f"text={self.BOT_NAME}", timeout=10_000)
            page.click(f"text={self.BOT_NAME}")

            # Extract new token from BotFather reply
            page.wait_for_selector(".message.out + .message", timeout=15_000)
            reply = page.inner_text(".message.out + .message")
            browser.close()

        # Token is in the format: 123456:ABCDEF...
        import re
        match = re.search(r"\d+:[A-Za-z0-9_-]{35,}", reply)
        if not match:
            raise ValueError(f"Could not extract token from BotFather reply: {reply}")
        new_token = match.group(0)
        log.info("telegram_bot: rotated successfully")
        return new_token
