"""Inventory: scan 1Password vaults and build the provider registry."""

from __future__ import annotations

import json
import logging
import os
import subprocess
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)

# Vaults Keymaster is authorised to read
TRACKED_VAULTS = ["hermes-agent", "Developer"]

# Tags / field names that identify rotatable API keys
ROTATABLE_TAG = "keymaster-rotate"


@dataclass
class KeyEntry:
    vault: str
    item_id: str
    item_title: str
    provider: str          # e.g. "openai", "anthropic"
    field_id: str          # 1P field ID to update
    current_value: str = ""


@dataclass
class Config:
    entries: list[KeyEntry] = field(default_factory=list)
    telegram_token: str = ""
    telegram_chat_id: str = ""
    glass_break_repo: str = ""
    glass_break_token: str = ""
    glass_break_passphrase: str = ""
    dry_run: bool = False


def load_config() -> Config:
    """Build Config by scanning 1Password and reading env vars."""
    cfg = Config(
        telegram_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
        glass_break_repo=os.getenv("GLASS_BREAK_REPO", ""),
        glass_break_token=os.getenv("GLASS_BREAK_GITHUB_TOKEN", ""),
        glass_break_passphrase=os.getenv("GLASS_BREAK_ENCRYPT_PASSPHRASE", ""),
        dry_run=os.getenv("KEYMASTER_DRY_RUN", "false").lower() == "true",
    )
    cfg.entries = _scan_vaults()
    return cfg


def _scan_vaults() -> list[KeyEntry]:
    entries: list[KeyEntry] = []
    for vault in TRACKED_VAULTS:
        try:
            items = _op_list_items(vault)
        except Exception as exc:
            log.warning("Could not scan vault %s: %s", vault, exc)
            continue
        for item in items:
            if ROTATABLE_TAG in item.get("tags", []):
                try:
                    entry = _op_get_entry(vault, item)
                    entries.append(entry)
                except Exception as exc:
                    log.warning("Skipping item %s: %s", item.get("title"), exc)
    log.info("inventory: found %d rotatable entries across vaults %s", len(entries), TRACKED_VAULTS)
    return entries


def _op_list_items(vault: str) -> list[dict]:
    result = subprocess.run(
        ["op", "item", "list", "--vault", vault, "--format", "json"],
        check=True, capture_output=True, text=True,
    )
    return json.loads(result.stdout)


def _op_get_entry(vault: str, item: dict[str, Any]) -> KeyEntry:
    result = subprocess.run(
        ["op", "item", "get", item["id"], "--vault", vault, "--format", "json"],
        check=True, capture_output=True, text=True,
    )
    detail = json.loads(result.stdout)
    provider = _extract_label(detail, "provider") or item["title"].lower().replace(" ", "_")
    api_field = _find_api_field(detail)
    return KeyEntry(
        vault=vault,
        item_id=item["id"],
        item_title=item["title"],
        provider=provider,
        field_id=api_field["id"],
        current_value=api_field.get("value", ""),
    )


def _extract_label(detail: dict, label: str) -> str:
    for field in detail.get("fields", []):
        if field.get("label", "").lower() == label.lower():
            return field.get("value", "")
    return ""


def _find_api_field(detail: dict) -> dict:
    """Return the first field whose type is CONCEALED (API key / password)."""
    for field in detail.get("fields", []):
        if field.get("type") == "CONCEALED":
            return field
    raise ValueError(f"No CONCEALED field in item {detail.get('title')}")
