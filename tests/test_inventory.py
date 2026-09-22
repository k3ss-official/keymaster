"""Tests for inventory / config loading (no live `op` calls)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from core.inventory import KeyEntry, load_config, _find_api_field, _op_get_entry


def test_load_config_reads_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    monkeypatch.setenv("KEYMASTER_DRY_RUN", "true")
    monkeypatch.setenv("GLASS_BREAK_REPO", "org/vault")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "proj-1")

    with patch("core.inventory._scan_vaults", return_value=[]):
        cfg = load_config()

    assert cfg.telegram_token == "tok"
    assert cfg.telegram_chat_id == "42"
    assert cfg.dry_run is True
    assert cfg.glass_break_repo == "org/vault"
    assert cfg.google_cloud_project == "proj-1"
    assert cfg.entries == []


def test_load_config_skip_scan(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    cfg = load_config(scan=False)
    assert cfg.entries == []


def test_find_api_field():
    detail = {
        "title": "OpenAI",
        "fields": [
            {"id": "a", "label": "username", "type": "STRING", "value": "x"},
            {"id": "b", "label": "credential", "type": "CONCEALED", "value": "sk-1"},
        ],
    }
    field = _find_api_field(detail)
    assert field["id"] == "b"
    assert field["value"] == "sk-1"


def test_op_get_entry_builds_key_entry():
    item = {"id": "item-1", "title": "OpenAI Key", "tags": ["keymaster-rotate"]}
    detail = {
        "title": "OpenAI Key",
        "fields": [
            {"id": "p", "label": "provider", "type": "STRING", "value": "openai"},
            {"id": "s", "label": "credential", "type": "CONCEALED", "value": "sk-live"},
        ],
    }
    completed = MagicMock()
    completed.stdout = json.dumps(detail)

    with patch("subprocess.run", return_value=completed):
        entry = _op_get_entry("Developer", item)

    assert isinstance(entry, KeyEntry)
    assert entry.provider == "openai"
    assert entry.field_label == "credential"
    assert entry.current_value == "sk-live"
    assert entry.vault == "Developer"
