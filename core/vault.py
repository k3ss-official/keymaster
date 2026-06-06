"""1Password vault read/write via the `op` CLI."""

from __future__ import annotations

import logging
import subprocess

from core.inventory import KeyEntry

log = logging.getLogger(__name__)


class Vault:
    """Thin wrapper around the 1Password CLI."""

    def read(self, entry: KeyEntry) -> str:
        """Return the current secret value for *entry*."""
        result = subprocess.run(
            [
                "op", "item", "get", entry.item_id,
                "--vault", entry.vault,
                "--fields", f"label={entry.field_id}",
                "--reveal",
            ],
            check=True, capture_output=True, text=True,
        )
        return result.stdout.strip()

    def write(self, entry: KeyEntry, new_value: str) -> None:
        """Overwrite the secret field in 1Password with *new_value*."""
        log.info("vault.write: updating %s / %s", entry.vault, entry.item_title)
        subprocess.run(
            [
                "op", "item", "edit", entry.item_id,
                "--vault", entry.vault,
                f"{entry.field_id}={new_value}",
            ],
            check=True, capture_output=True, text=True,
        )
