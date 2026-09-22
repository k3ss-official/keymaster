"""Vault + notify unit tests (mocked)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.inventory import KeyEntry
from core.notify import Notifier, RotationResult
from core.vault import Vault, VaultError


def _entry() -> KeyEntry:
    return KeyEntry(
        vault="Developer",
        item_id="abc",
        item_title="OpenAI",
        provider="openai",
        field_id="f",
        field_label="credential",
        current_value="sk",
    )


def test_vault_write_uses_field_label():
    completed = MagicMock(stdout="", returncode=0)
    with patch("subprocess.run", return_value=completed) as run:
        Vault().write(_entry(), "sk-new")
    cmd = run.call_args.args[0]
    assert "credential=sk-new" in cmd
    assert "--vault" in cmd


def test_vault_missing_op():
    with patch("subprocess.run", side_effect=FileNotFoundError("op")):
        with pytest.raises(VaultError, match="op"):
            Vault().read(_entry())


def test_notifier_skips_when_unconfigured():
    Notifier("", "").send_report([RotationResult("openai", True)])


def test_notifier_format_includes_dry_run():
    text = Notifier._format(
        [RotationResult("openai", True, "would rotate", dry_run=True)]
    )
    assert "dry-run" in text
    assert "openai" in text
