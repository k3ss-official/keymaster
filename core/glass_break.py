"""Glass-break: encrypted backup of rotated credentials to a private GitHub repo."""

from __future__ import annotations

import base64
import datetime
import logging
import subprocess
import tempfile
from pathlib import Path

from github import Github

log = logging.getLogger(__name__)


class GlassBreak:
    """Pushes a GPG-encrypted JSON snapshot to a private vault repo."""

    def __init__(self, github_token: str, repo_name: str, passphrase: str) -> None:
        self._gh = Github(github_token)
        self._repo = self._gh.get_repo(repo_name)
        self._passphrase = passphrase

    # ------------------------------------------------------------------ #
    #  Public API                                                           #
    # ------------------------------------------------------------------ #

    def push(self, snapshot: dict) -> str:
        """Encrypt *snapshot* and push to vault repo.  Returns commit SHA."""
        import json

        plaintext = json.dumps(snapshot, indent=2).encode()
        ciphertext = self._encrypt(plaintext)
        filename = self._filename()
        commit = self._write_file(filename, ciphertext)
        log.info("glass-break: pushed %s → %s", filename, commit)
        return commit

    # ------------------------------------------------------------------ #
    #  Internals                                                            #
    # ------------------------------------------------------------------ #

    def _encrypt(self, plaintext: bytes) -> bytes:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(plaintext)
            tmp_path = Path(tmp.name)
        out_path = tmp_path.with_suffix(".gpg")
        subprocess.run(
            [
                "gpg", "--batch", "--yes",
                "--passphrase", self._passphrase,
                "--symmetric", "--cipher-algo", "AES256",
                "--output", str(out_path),
                str(tmp_path),
            ],
            check=True,
            capture_output=True,
        )
        ciphertext = out_path.read_bytes()
        tmp_path.unlink(missing_ok=True)
        out_path.unlink(missing_ok=True)
        return ciphertext

    def _filename(self) -> str:
        ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        return f"snapshots/{ts}.json.gpg"

    def _write_file(self, path: str, data: bytes) -> str:
        content_b64 = base64.b64encode(data).decode()
        try:
            existing = self._repo.get_contents(path)
            result = self._repo.update_file(
                path, f"snapshot {path}", data, existing.sha
            )
        except Exception:
            result = self._repo.create_file(
                path, f"snapshot {path}", data
            )
        return result["commit"].sha
