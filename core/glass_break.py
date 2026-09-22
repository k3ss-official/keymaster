"""Glass-break: encrypted backup of rotated credentials to a private GitHub repo."""

from __future__ import annotations

import datetime
import json
import logging
import subprocess
import tempfile
from pathlib import Path

from github import Github
from github.GithubException import UnknownObjectException

log = logging.getLogger(__name__)


class GlassBreakError(RuntimeError):
    """Raised when encryption or vault push fails."""


class GlassBreak:
    """Pushes a GPG-encrypted JSON snapshot to a private vault repo."""

    def __init__(self, github_token: str, repo_name: str, passphrase: str) -> None:
        if not github_token:
            raise GlassBreakError("GLASS_BREAK_GITHUB_TOKEN is required")
        if not repo_name:
            raise GlassBreakError("GLASS_BREAK_REPO is required")
        if not passphrase:
            raise GlassBreakError("GLASS_BREAK_ENCRYPT_PASSPHRASE is required")
        self._gh = Github(github_token)
        self._repo = self._gh.get_repo(repo_name)
        self._passphrase = passphrase

    def push(self, snapshot: dict) -> str:
        """Encrypt *snapshot* and push to vault repo. Returns commit SHA."""
        plaintext = json.dumps(snapshot, indent=2, sort_keys=True).encode()
        ciphertext = self._encrypt(plaintext)
        filename = self._filename()
        commit = self._write_file(filename, ciphertext)
        log.info("glass-break: pushed %s → %s", filename, commit)
        return commit

    def _encrypt(self, plaintext: bytes) -> bytes:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / "snapshot.json"
            out_path = Path(tmpdir) / "snapshot.json.gpg"
            tmp_path.write_bytes(plaintext)
            try:
                subprocess.run(
                    [
                        "gpg",
                        "--batch",
                        "--yes",
                        "--pinentry-mode",
                        "loopback",
                        "--passphrase",
                        self._passphrase,
                        "--symmetric",
                        "--cipher-algo",
                        "AES256",
                        "--output",
                        str(out_path),
                        str(tmp_path),
                    ],
                    check=True,
                    capture_output=True,
                )
            except FileNotFoundError as exc:
                raise GlassBreakError(
                    "`gpg` not found — install GnuPG for glass-break backups"
                ) from exc
            except subprocess.CalledProcessError as exc:
                stderr = (exc.stderr or b"").decode(errors="replace").strip()
                raise GlassBreakError(f"gpg encrypt failed: {stderr}") from exc
            return out_path.read_bytes()

    def _filename(self) -> str:
        ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        return f"snapshots/{ts}.json.gpg"

    def _write_file(self, path: str, data: bytes) -> str:
        # PyGithub Contents API expects a str; preserve binary via latin-1 round-trip.
        content = data.decode("latin-1")
        message = f"keymaster glass-break snapshot {path}"
        try:
            existing = self._repo.get_contents(path)
            # get_contents may return a list for directories; snapshots are files.
            if isinstance(existing, list):
                raise GlassBreakError(f"path {path} is a directory, not a file")
            result = self._repo.update_file(path, message, content, existing.sha)
        except UnknownObjectException:
            result = self._repo.create_file(path, message, content)
        return result["commit"].sha
