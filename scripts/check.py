#!/usr/bin/env python3
"""Validate packs without building: what a contributor runs before opening a PR."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import packlib  # noqa: E402


def main() -> int:
    packs = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "packs"
    failed = False
    for directory in sorted(p for p in packs.iterdir() if p.is_dir()):
        try:
            manifest = packlib.load_pack(directory)
            count = f"{len(manifest['items'])} items" if manifest["kind"] == "prompts" else "rules"
            print(f"ok    {manifest['id']} {manifest['version']} ({count})")
        except packlib.PackError as error:
            failed = True
            print(f"FAIL  {error}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
