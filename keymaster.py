#!/usr/bin/env python3
"""
Keymaster — top-level CLI entry point.

Usage:
    python keymaster.py --audit      # inventory only, no changes
    python keymaster.py --rotate     # full rotation cycle
    python keymaster.py --validate   # validate current keys
    python keymaster.py --provider openai --rotate   # single-provider rotation
"""

import argparse
import logging
import sys
from pathlib import Path

# Ensure repo root is on the path when run directly
sys.path.insert(0, str(Path(__file__).parent))

from core.runner import Runner
from core.inventory import load_config


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="keymaster",
        description="Janet-owned automated API key rotation system",
    )
    p.add_argument("--audit", action="store_true", help="Inventory scan only — no changes")
    p.add_argument("--rotate", action="store_true", help="Full rotation cycle")
    p.add_argument("--validate", action="store_true", help="Validate current keys")
    p.add_argument("--provider", metavar="NAME", help="Limit to a single provider")
    p.add_argument("--dry-run", action="store_true", help="Simulate without writing back")
    p.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    return p


def main() -> None:
    args = build_parser().parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )

    if not any([args.audit, args.rotate, args.validate]):
        build_parser().print_help()
        sys.exit(0)

    config = load_config()
    runner = Runner(config, dry_run=args.dry_run)

    if args.audit:
        runner.audit(provider=args.provider)
    elif args.validate:
        runner.validate(provider=args.provider)
    elif args.rotate:
        runner.rotate(provider=args.provider)


if __name__ == "__main__":
    main()
