#!/usr/bin/env python3
"""
Keymaster — top-level CLI entry point.

Usage:
    python keymaster.py --audit      # inventory only, no changes
    python keymaster.py --rotate     # full rotation cycle
    python keymaster.py --validate   # validate current keys
    python keymaster.py --provider openai --rotate   # single-provider rotation
    python keymaster.py --rotate --dry-run           # plan rotation, no live calls
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Ensure repo root is on the path when run directly (editable install preferred)
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

from core.inventory import load_config
from core.runner import Runner


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="keymaster",
        description="Janet-owned automated API key rotation system",
    )
    p.add_argument("--audit", action="store_true", help="Inventory scan only — no changes")
    p.add_argument("--rotate", action="store_true", help="Full rotation cycle")
    p.add_argument("--validate", action="store_true", help="Validate current keys")
    p.add_argument("--provider", metavar="NAME", help="Limit to a single provider")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate without calling provider rotate APIs or writing back",
    )
    p.add_argument(
        "--log-level",
        default=None,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Override KEYMASTER_LOG_LEVEL (default INFO)",
    )
    p.add_argument(
        "--list-providers",
        action="store_true",
        help="Print known rotator providers and exit",
    )
    return p


def main() -> None:
    load_dotenv(_ROOT / ".env")
    args = build_parser().parse_args()

    if args.list_providers:
        from core.runner import PROVIDER_MAP

        for name, module in sorted(PROVIDER_MAP.items()):
            print(f"{name:16}  {module}")
        sys.exit(0)

    if not any([args.audit, args.rotate, args.validate]):
        build_parser().print_help()
        sys.exit(0)

    import os

    log_level = args.log_level or os.getenv("KEYMASTER_LOG_LEVEL", "INFO")
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )

    config = load_config()
    dry_run = args.dry_run or config.dry_run
    if dry_run:
        logging.getLogger(__name__).info("dry-run enabled — no live rotations or vault writes")

    runner = Runner(config, dry_run=dry_run)
    ok = True
    if args.audit:
        ok = runner.audit(provider=args.provider)
    elif args.validate:
        ok = runner.validate(provider=args.provider)
    elif args.rotate:
        ok = runner.rotate(provider=args.provider)

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
