"""Glass-break unit tests (mocked gpg + GitHub)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.glass_break import GlassBreak, GlassBreakError


def test_glass_break_requires_passphrase():
    with pytest.raises(GlassBreakError):
        GlassBreak("token", "org/repo", "")


def test_encrypt_and_push(tmp_path):
    fake_gpg = b"\x00ENCRYPTED\x00"
    repo = MagicMock()
    commit = MagicMock()
    commit.sha = "abc123"
    repo.get_contents.side_effect = __import__(
        "github.GithubException", fromlist=["UnknownObjectException"]
    ).UnknownObjectException(404, {"message": "missing"}, headers={})
    repo.create_file.return_value = {"commit": commit}

    gh = MagicMock()
    gh.get_repo.return_value = repo

    with (
        patch("core.glass_break.Github", return_value=gh),
        patch("subprocess.run") as run,
    ):
        # Simulate gpg writing the output file
        def _gpg(cmd, **kwargs):
            out = cmd[cmd.index("--output") + 1]
            from pathlib import Path

            Path(out).write_bytes(fake_gpg)
            return MagicMock(returncode=0)

        run.side_effect = _gpg
        gb = GlassBreak("token", "org/repo", "secret-pass")
        sha = gb.push({"openai": "sk-new"})

    assert sha == "abc123"
    repo.create_file.assert_called_once()
    args = repo.create_file.call_args.args
    assert args[0].startswith("snapshots/")
    assert args[0].endswith(".json.gpg")
    assert args[2].encode("latin-1") == fake_gpg
