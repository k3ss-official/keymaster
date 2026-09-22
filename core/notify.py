"""Telegram notification helper."""

from __future__ import annotations

import logging
from dataclasses import dataclass

log = logging.getLogger(__name__)


@dataclass
class RotationResult:
    provider: str
    success: bool
    message: str = ""
    dry_run: bool = False


class Notifier:
    def __init__(self, token: str, chat_id: str) -> None:
        self._token = token
        self._chat_id = chat_id

    @property
    def configured(self) -> bool:
        return bool(self._token and self._chat_id)

    def send_report(self, results: list[RotationResult]) -> None:
        if not self.configured:
            log.warning("Telegram not configured — skipping notification")
            return
        if not results:
            log.info("notify: no results to report")
            return
        try:
            import asyncio

            import telegram  # python-telegram-bot

            text = self._format(results)
            bot = telegram.Bot(token=self._token)

            async def _send() -> None:
                await bot.send_message(
                    chat_id=self._chat_id,
                    text=text,
                    parse_mode="HTML",
                )

            asyncio.run(_send())
            log.info("notify: Telegram report sent")
        except Exception as exc:
            log.error("notify: failed to send Telegram report: %s", exc)

    @staticmethod
    def _format(results: list[RotationResult]) -> str:
        lines = ["<b>🔑 Keymaster Rotation Report</b>\n"]
        if any(r.dry_run for r in results):
            lines.append("<i>(dry-run — no live changes)</i>\n")
        ok = [r for r in results if r.success]
        fail = [r for r in results if not r.success]
        for r in ok:
            suffix = f" — {r.message}" if r.message else ""
            lines.append(f"✅ <code>{r.provider}</code>{suffix}")
        for r in fail:
            lines.append(f"❌ <code>{r.provider}</code> — {r.message}")
        lines.append(f"\n<i>{len(ok)}/{len(results)} succeeded</i>")
        return "\n".join(lines)
