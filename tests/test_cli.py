"""CLI smoke tests (no live services)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import keymaster


def test_list_providers(capsys):
    with patch("sys.argv", ["keymaster", "--list-providers"]):
        try:
            keymaster.main()
        except SystemExit as exc:
            assert exc.code == 0
    out = capsys.readouterr().out
    assert "openai" in out
    assert "rotators.api.openai" in out


def test_help_exits_zero_without_action():
    with patch("sys.argv", ["keymaster"]):
        try:
            keymaster.main()
        except SystemExit as exc:
            assert exc.code == 0


def test_audit_wires_runner(monkeypatch):
    monkeypatch.setattr(keymaster, "load_dotenv", lambda *a, **k: None)
    cfg = MagicMock()
    cfg.dry_run = False
    runner = MagicMock()
    runner.audit.return_value = True

    with (
        patch("sys.argv", ["keymaster", "--audit"]),
        patch("keymaster.load_config", return_value=cfg),
        patch("keymaster.Runner", return_value=runner),
    ):
        try:
            keymaster.main()
        except SystemExit as exc:
            assert exc.code == 0
    runner.audit.assert_called_once()
