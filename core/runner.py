"""Orchestrates the full rotation cycle."""

from __future__ import annotations

import importlib
import logging
from typing import Optional

from core.inventory import Config, KeyEntry
from core.notify import Notifier, RotationResult
from core.vault import Vault
from core.glass_break import GlassBreak

log = logging.getLogger(__name__)

# Map provider names → rotator module paths
PROVIDER_MAP: dict[str, str] = {
    "anthropic":    "rotators.api.anthropic",
    "openai":       "rotators.api.openai",
    "openrouter":   "rotators.api.openrouter",
    "github_pat":   "rotators.api.github_pat",
    "huggingface":  "rotators.api.huggingface",
    "tavily":       "rotators.api.tavily",
    "gemini":       "rotators.api.gemini",
    "deepseek":     "rotators.browser.deepseek",
    "meta":         "rotators.browser.meta",
    "telegram_bot": "rotators.browser.telegram_bot",
}


class Runner:
    def __init__(self, config: Config, dry_run: bool = False) -> None:
        self._cfg = config
        self._dry_run = dry_run or config.dry_run
        self._vault = Vault()
        self._notifier = Notifier(config.telegram_token, config.telegram_chat_id)

    # ------------------------------------------------------------------ #
    #  Public commands                                                      #
    # ------------------------------------------------------------------ #

    def audit(self, provider: Optional[str] = None) -> None:
        entries = self._filter(provider)
        log.info("audit: %d entries", len(entries))
        for e in entries:
            log.info("  [%s] %s / %s", e.vault, e.provider, e.item_title)

    def validate(self, provider: Optional[str] = None) -> None:
        entries = self._filter(provider)
        results = []
        for entry in entries:
            rotator = self._load_rotator(entry.provider)
            if rotator is None:
                continue
            ok, msg = rotator.validate(entry.current_value)
            results.append(RotationResult(entry.provider, ok, msg))
            log.info("validate %s: %s", entry.provider, "OK" if ok else msg)
        self._notifier.send_report(results)

    def rotate(self, provider: Optional[str] = None) -> None:
        entries = self._filter(provider)
        results = []
        snapshot: dict = {}

        for entry in entries:
            rotator = self._load_rotator(entry.provider)
            if rotator is None:
                log.warning("No rotator for provider %s — skipping", entry.provider)
                continue
            try:
                new_key = rotator.rotate(entry.current_value)
                if not self._dry_run:
                    self._vault.write(entry, new_key)
                snapshot[entry.provider] = new_key
                results.append(RotationResult(entry.provider, True))
                log.info("rotated %s OK", entry.provider)
            except Exception as exc:
                results.append(RotationResult(entry.provider, False, str(exc)))
                log.error("rotation failed for %s: %s", entry.provider, exc)

        if snapshot and not self._dry_run:
            self._push_glass_break(snapshot)

        self._notifier.send_report(results)

    # ------------------------------------------------------------------ #
    #  Internals                                                            #
    # ------------------------------------------------------------------ #

    def _filter(self, provider: Optional[str]) -> list[KeyEntry]:
        if provider:
            return [e for e in self._cfg.entries if e.provider == provider]
        return list(self._cfg.entries)

    def _load_rotator(self, provider: str):
        module_path = PROVIDER_MAP.get(provider)
        if not module_path:
            return None
        try:
            mod = importlib.import_module(module_path)
            return mod.Rotator()
        except Exception as exc:
            log.error("Could not load rotator %s: %s", module_path, exc)
            return None

    def _push_glass_break(self, snapshot: dict) -> None:
        if not self._cfg.glass_break_token:
            log.warning("glass-break not configured — skipping")
            return
        try:
            gb = GlassBreak(
                self._cfg.glass_break_token,
                self._cfg.glass_break_repo,
                self._cfg.glass_break_passphrase,
            )
            gb.push(snapshot)
        except Exception as exc:
            log.error("glass-break push failed: %s", exc)
