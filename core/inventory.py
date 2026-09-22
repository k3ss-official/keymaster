"""Inventory: scan 1Password vaults and build the provider registry."""

from __future__ import annotations

import json
import logging
import os
import shutil
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
    provider: str  # e.g. "openai", "anthropic"
    field_id: str  # 1P field ID (for reference)
    field_label: str  # 1P field label used by `op item edit`
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
    google_cloud_project: str = ""


def load_config(*, scan: bool = True) -> Config:
    """Build Config from env vars, optionally scanning 1Password for entries."""
    cfg = Config(
        telegram_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
        glass_break_repo=os.getenv("GLASS_BREAK_REPO", "k3ss-official/keymaster-vault"),
        glass_break_token=os.getenv("GLASS_BREAK_GITHUB_TOKEN", ""),
        glass_break_passphrase=os.getenv("GLASS_BREAK_ENCRYPT_PASSPHRASE", ""),
        dry_run=os.getenv("KEYMASTER_DRY_RUN", "false").lower() in {"1", "true", "yes"},
        google_cloud_project=os.getenv("GOOGLE_CLOUD_PROJECT", ""),
    )
    if scan:
        cfg.entries = _scan_vaults()
    return cfg


def op_available() -> bool:
    """Return True if the 1Password CLI is on PATH."""
    return shutil.which("op") is not None


def _scan_vaults() -> list[KeyEntry]:
    if not op_available():
        log.warning(
            "1Password CLI (`op`) not found — inventory empty. "
            "Install from https://1password.com/downloads/command-line/ and run `op signin`."
        )
        return []

    entries: list[KeyEntry] = []
    for vault in TRACKED_VAULTS:
        try:
            items = _op_list_items(vault)
        except Exception as exc:
            log.warning("Could not scan vault %s: %s", vault, exc)
            continue
        for item in items:
            tags = item.get("tags") or []
            if ROTATABLE_TAG not in tags:
                continue
            try:
                entry = _op_get_entry(vault, item)
                entries.append(entry)
            except Exception as exc:
                log.warning("Skipping item %s: %s", item.get("title"), exc)
    log.info(
        "inventory: found %d rotatable entries across vaults %s",
        len(entries),
        TRACKED_VAULTS,
    )
    return entries


def _op_list_items(vault: str) -> list[dict[str, Any]]:
    result = subprocess.run(
        ["op", "item", "list", "--vault", vault, "--format", "json"],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout or "[]")
    if not isinstance(data, list):
        raise ValueError(f"unexpected op list payload for vault {vault}")
    return data


def _op_get_entry(vault: str, item: dict[str, Any]) -> KeyEntry:
    result = subprocess.run(
        ["op", "item", "get", item["id"], "--vault", vault, "--format", "json"],
        check=True,
        capture_output=True,
        text=True,
    )
    detail = json.loads(result.stdout)
    provider = (
        _extract_label(detail, "provider")
        or str(item.get("title", "")).lower().replace(" ", "_")
    )
    api_field = _find_api_field(detail)
    label = api_field.get("label") or api_field.get("id")
    if not label:
        raise ValueError(f"API field missing label in item {detail.get('title')}")
    return KeyEntry(
        vault=vault,
        item_id=item["id"],
        item_title=item.get("title", item["id"]),
        provider=provider.strip().lower(),
        field_id=str(api_field.get("id", "")),
        field_label=str(label),
        current_value=str(api_field.get("value") or ""),
    )


def _extract_label(detail: dict[str, Any], label: str) -> str:
    for field_obj in detail.get("fields", []):
        if str(field_obj.get("label", "")).lower() == label.lower():
            return str(field_obj.get("value") or "")
    return ""


def _find_api_field(detail: dict[str, Any]) -> dict[str, Any]:
    """Return the first field whose type is CONCEALED (API key / password)."""
    for field_obj in detail.get("fields", []):
        if field_obj.get("type") == "CONCEALED":
            return field_obj
    raise ValueError(f"No CONCEALED field in item {detail.get('title')}")
