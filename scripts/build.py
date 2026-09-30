#!/usr/bin/env python3
"""Build every pack into dist/ (archives plus index.json), then verify the result."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import packlib  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packs", default=str(ROOT / "packs"))
    parser.add_argument("--out", default=str(ROOT / "dist"))
    parser.add_argument(
        "--base-url",
        default=os.environ.get("EXT_BASE_URL", "https://github.com/Jia-Ethan/keysmith-switch-extensions/releases/latest/download"),
        help="where the archives will be downloaded from",
    )
    parser.add_argument("--generated-at", default=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    args = parser.parse_args()
    try:
        index = packlib.build_index(Path(args.packs), Path(args.out), args.base_url, args.generated_at)
        packlib.verify_release(Path(args.out))
    except packlib.PackError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    for entry in index["packs"]:
        print(f"{entry['id']} {entry['version']}  {entry['size']} bytes  sha256:{entry['sha256'][:12]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
