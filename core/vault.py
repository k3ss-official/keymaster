"""1Password vault read/write via the `op` CLI."""

from __future__ import annotations

import logging
import subprocess

from core.inventory import KeyEntry

log = logging.getLogger(__name__)


class VaultError(RuntimeError):
    """Raised when a 1Password CLI operation fails."""


class Vault:
    """Thin wrapper around the 1Password CLI."""

    def read(self, entry: KeyEntry) -> str:
        """Return the current secret value for *entry*."""
        result = self._run(
            [
                "op",
                "item",
                "get",
                entry.item_id,
                "--vault",
                entry.vault,
                "--fields",
                entry.field_label,
                "--reveal",
            ]
        )
        return result.stdout.strip()

    def write(self, entry: KeyEntry, new_value: str) -> None:
        """Overwrite the secret field in 1Password with *new_value*."""
        log.info("vault.write: updating %s / %s", entry.vault, entry.item_title)
        self._run(
            [
                "op",
                "item",
                "edit",
                entry.item_id,
                "--vault",
                entry.vault,
                f"{entry.field_label}={new_value}",
            ]
        )

    @staticmethod
    def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            raise VaultError(
                "1Password CLI (`op`) not found — install and authenticate first"
            ) from exc
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or "").strip() or str(exc)
            raise VaultError(f"op failed ({exc.returncode}): {stderr}") from exc
