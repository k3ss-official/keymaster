"""Orchestrates the full rotation cycle."""

from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass
from typing import Optional

from core.glass_break import GlassBreak
from core.inventory import Config, KeyEntry, op_available
from core.notify import Notifier, RotationResult
from core.vault import Vault

log = logging.getLogger(__name__)

# Map provider names → rotator module paths
PROVIDER_MAP: dict[str, str] = {
    "anthropic": "rotators.api.anthropic",
    "openai": "rotators.api.openai",
    "openrouter": "rotators.api.openrouter",
    "github_pat": "rotators.api.github_pat",
    "huggingface": "rotators.api.huggingface",
    "tavily": "rotators.api.tavily",
    "gemini": "rotators.api.gemini",
    "deepseek": "rotators.browser.deepseek",
    "meta": "rotators.browser.meta",
    "telegram_bot": "rotators.browser.telegram_bot",
}


@dataclass
class _LiveRotation:
    """Internal: successful live rotation carrying the new secret for glass-break."""

    result: RotationResult
    new_key: str = ""


class Runner:
    def __init__(self, config: Config, dry_run: bool = False) -> None:
        self._cfg = config
        self._dry_run = dry_run or config.dry_run
        self._vault = Vault()
        self._notifier = Notifier(config.telegram_token, config.telegram_chat_id)

    # ------------------------------------------------------------------ #
    #  Public commands                                                     #
    # ------------------------------------------------------------------ #

    def audit(self, provider: Optional[str] = None) -> bool:
        """Inventory scan. Returns True if the scan completed (even if empty)."""
        if not op_available():
            log.error("audit requires 1Password CLI (`op`) — see README")
            return False

        entries = self._filter(provider)
        log.info("audit: %d entries (dry_run=%s)", len(entries), self._dry_run)
        if not entries:
            log.warning(
                "No rotatable items found. Tag 1Password items with `keymaster-rotate` "
                "in vaults %s.",
                ["hermes-agent", "Developer"],
            )
            return True

        for e in entries:
            has_secret = "yes" if e.current_value else "MISSING"
            log.info(
                "  [%s] provider=%s item=%s field=%s secret=%s",
                e.vault,
                e.provider,
                e.item_title,
                e.field_label,
                has_secret,
            )
            if e.provider not in PROVIDER_MAP:
                log.warning("  → no rotator registered for provider %r", e.provider)
        return True

    def validate(self, provider: Optional[str] = None) -> bool:
        entries = self._filter(provider)
        if not entries:
            log.warning("validate: nothing to check")
            return True

        results: list[RotationResult] = []
        for entry in entries:
            rotator = self._load_rotator(entry.provider)
            if rotator is None:
                results.append(
                    RotationResult(entry.provider, False, "no rotator registered")
                )
                continue
            if not entry.current_value:
                results.append(
                    RotationResult(entry.provider, False, "empty secret in vault")
                )
                continue
            try:
                ok, msg = rotator.validate(entry.current_value)
            except Exception as exc:
                ok, msg = False, str(exc)
            results.append(RotationResult(entry.provider, ok, msg))
            log.info("validate %s: %s", entry.provider, "OK" if ok else msg)

        if not self._dry_run:
            self._notifier.send_report(results)
        return all(r.success for r in results)

    def rotate(self, provider: Optional[str] = None) -> bool:
        entries = self._filter(provider)
        if not entries:
            log.warning("rotate: nothing to rotate")
            return True

        results: list[RotationResult] = []
        snapshot: dict[str, str] = {}

        for entry in entries:
            live = self._rotate_one(entry)
            results.append(live.result)
            if live.new_key:
                snapshot[entry.provider] = live.new_key

        if snapshot and not self._dry_run:
            self._push_glass_break(snapshot)

        if not self._dry_run:
            self._notifier.send_report(results)
        else:
            log.info("dry-run: skipping Telegram report and glass-break")

        return all(r.success for r in results)

    # ------------------------------------------------------------------ #
    #  Internals                                                           #
    # ------------------------------------------------------------------ #

    def _rotate_one(self, entry: KeyEntry) -> _LiveRotation:
        rotator = self._load_rotator(entry.provider)
        if rotator is None:
            log.warning("No rotator for provider %s — skipping", entry.provider)
            return _LiveRotation(
                RotationResult(entry.provider, False, "no rotator registered")
            )

        if self._dry_run:
            log.info(
                "dry-run: would rotate %s (%s / %s)",
                entry.provider,
                entry.vault,
                entry.item_title,
            )
            return _LiveRotation(
                RotationResult(
                    entry.provider,
                    True,
                    "would rotate (dry-run)",
                    dry_run=True,
                )
            )

        if not entry.current_value:
            return _LiveRotation(
                RotationResult(entry.provider, False, "empty secret in vault")
            )

        try:
            new_key = rotator.rotate(entry.current_value)
            if not new_key or new_key == entry.current_value:
                return _LiveRotation(
                    RotationResult(
                        entry.provider,
                        False,
                        "rotator returned empty or unchanged key",
                    )
                )

            ok, msg = rotator.validate(new_key)
            if not ok:
                return _LiveRotation(
                    RotationResult(
                        entry.provider,
                        False,
                        f"new key failed validation: {msg}",
                    )
                )

            self._vault.write(entry, new_key)
            log.info("rotated %s OK", entry.provider)
            return _LiveRotation(RotationResult(entry.provider, True, "OK"), new_key)
        except Exception as exc:
            log.error("rotation failed for %s: %s", entry.provider, exc)
            return _LiveRotation(RotationResult(entry.provider, False, str(exc)))

    def _filter(self, provider: Optional[str]) -> list[KeyEntry]:
        if provider:
            wanted = provider.strip().lower()
            matched = [e for e in self._cfg.entries if e.provider == wanted]
            if not matched:
                log.warning("No inventory entries for provider %r", provider)
            return matched
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

    def _push_glass_break(self, snapshot: dict[str, str]) -> None:
        if not self._cfg.glass_break_token or not self._cfg.glass_break_passphrase:
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
