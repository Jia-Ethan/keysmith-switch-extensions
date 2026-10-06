#!/usr/bin/env python3
"""Fill in the sha256 of every listed file (prompts, or a rule pack's rules.json), then validate the pack.

    python3 scripts/seal.py packs/my.pack
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import packlib  # noqa: E402


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    directory = Path(sys.argv[1])
    manifest_path = directory / "pack.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for item in manifest.get("items", []):
        packlib.safe_relative_path(item["file"])
        item["sha256"] = packlib.sha256_hex((directory / item["file"]).read_bytes())
    rules = manifest.get("rules")
    if isinstance(rules, dict) and isinstance(rules.get("file"), str):
        packlib.safe_relative_path(rules["file"])
        rules["sha256"] = packlib.sha256_hex((directory / rules["file"]).read_bytes())
    manifest_path.write_bytes(packlib.canonical_json(manifest))
    try:
        packlib.load_pack(directory)
    except packlib.PackError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(f"sealed {directory}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
