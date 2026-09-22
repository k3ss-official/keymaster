"""Runner orchestration tests — mocked rotators / vault (no live APIs)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from core.inventory import Config, KeyEntry
from core.runner import PROVIDER_MAP, Runner


def _entry(provider: str = "openai", value: str = "sk-old") -> KeyEntry:
    return KeyEntry(
        vault="Developer",
        item_id="id-1",
        item_title="OpenAI",
        provider=provider,
        field_id="f1",
        field_label="credential",
        current_value=value,
    )


def test_provider_map_covers_readme_providers():
    expected = {
        "anthropic",
        "openai",
        "openrouter",
        "github_pat",
        "huggingface",
        "tavily",
        "gemini",
        "deepseek",
        "meta",
        "telegram_bot",
    }
    assert set(PROVIDER_MAP) == expected


def test_audit_lists_entries():
    cfg = Config(entries=[_entry()])
    runner = Runner(cfg, dry_run=True)
    with patch("core.runner.op_available", return_value=True):
        assert runner.audit() is True


def test_audit_fails_without_op():
    cfg = Config(entries=[_entry()])
    runner = Runner(cfg)
    with patch("core.runner.op_available", return_value=False):
        assert runner.audit() is False


def test_dry_run_rotate_does_not_call_rotator_or_vault():
    cfg = Config(entries=[_entry()])
    runner = Runner(cfg, dry_run=True)
    mock_rotator = MagicMock()
    with (
        patch.object(runner, "_load_rotator", return_value=mock_rotator),
        patch.object(runner._vault, "write") as write,
        patch.object(runner, "_push_glass_break") as gb,
        patch.object(runner._notifier, "send_report") as notify,
    ):
        ok = runner.rotate()
    assert ok is True
    mock_rotator.rotate.assert_not_called()
    write.assert_not_called()
    gb.assert_not_called()
    notify.assert_not_called()


def test_live_rotate_validates_then_writes():
    cfg = Config(entries=[_entry()])
    runner = Runner(cfg, dry_run=False)
    mock_rotator = MagicMock()
    mock_rotator.rotate.return_value = "sk-new"
    mock_rotator.validate.return_value = (True, "OK")

    with (
        patch.object(runner, "_load_rotator", return_value=mock_rotator),
        patch.object(runner._vault, "write") as write,
        patch.object(runner, "_push_glass_break") as gb,
        patch.object(runner._notifier, "send_report") as notify,
    ):
        ok = runner.rotate()

    assert ok is True
    mock_rotator.rotate.assert_called_once_with("sk-old")
    mock_rotator.validate.assert_called_once_with("sk-new")
    write.assert_called_once()
    gb.assert_called_once_with({"openai": "sk-new"})
    notify.assert_called_once()


def test_live_rotate_aborts_write_if_new_key_invalid():
    cfg = Config(entries=[_entry()])
    runner = Runner(cfg, dry_run=False)
    mock_rotator = MagicMock()
    mock_rotator.rotate.return_value = "sk-bad"
    mock_rotator.validate.return_value = (False, "HTTP 401")

    with (
        patch.object(runner, "_load_rotator", return_value=mock_rotator),
        patch.object(runner._vault, "write") as write,
        patch.object(runner, "_push_glass_break") as gb,
        patch.object(runner._notifier, "send_report"),
    ):
        ok = runner.rotate()

    assert ok is False
    write.assert_not_called()
    gb.assert_not_called()


def test_validate_reports_failure():
    cfg = Config(entries=[_entry()])
    runner = Runner(cfg, dry_run=False)
    mock_rotator = MagicMock()
    mock_rotator.validate.return_value = (False, "HTTP 401")

    with (
        patch.object(runner, "_load_rotator", return_value=mock_rotator),
        patch.object(runner._notifier, "send_report") as notify,
    ):
        ok = runner.validate()

    assert ok is False
    notify.assert_called_once()


def test_unknown_provider_filter():
    cfg = Config(entries=[_entry("openai")])
    runner = Runner(cfg, dry_run=True)
    assert runner.rotate(provider="nope") is True  # nothing matched → success/no-op
