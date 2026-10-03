"""Offline checks for the official content and its published archive."""

import io
import json
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import packlib  # noqa: E402


TOOLS = ("codex", "claude", "grok", "zcode")
PACKS = {tool: f"keysmith.{tool}" for tool in TOOLS}


class OfficialPromptsTest(unittest.TestCase):
    def setUp(self):
        self.manifests = {tool: packlib.load_pack(ROOT / "packs" / pack_id) for tool, pack_id in PACKS.items()}
        self.sources = json.loads((ROOT / "docs/prompt-sources.json").read_text(encoding="utf-8"))

    def test_each_official_prompt_is_its_own_pack(self):
        for retired in ("keysmith.example", "keysmith.core"):
            self.assertFalse((ROOT / "packs" / retired).exists())
        self.assertEqual({path.name for path in (ROOT / "packs").iterdir()}, set(PACKS.values()))
        for tool, manifest in self.manifests.items():
            with self.subTest(tool=tool):
                self.assertEqual(manifest["id"], PACKS[tool])
                self.assertEqual(manifest["tools"], [tool])
                self.assertEqual([(item["id"], item["tool"]) for item in manifest["items"]], [(f"{tool}-keysmith", tool)])

    def test_prompt_bytes_match_the_recorded_sources(self):
        records = self.sources["prompts"]
        self.assertEqual(len(records), 4)
        by_tool = {record["tool"]: record for record in records}
        self.assertEqual(set(by_tool), set(TOOLS))
        for tool, manifest in self.manifests.items():
            with self.subTest(tool=tool):
                record = by_tool[tool]
                (item,) = manifest["items"]
                self.assertEqual(record["pack_id"], manifest["id"])
                self.assertEqual(self.sources["pack_version"], manifest["version"])
                self.assertRegex(record["commit"], r"^[0-9a-f]{40}$")
                self.assertEqual(record["output"], item["file"])
                digest = packlib.sha256_hex((ROOT / "packs" / manifest["id"] / item["file"]).read_bytes())
                self.assertEqual(digest, record["sha256"])
                if tool == "claude":
                    self.assertEqual(record["transform"], "claude-main-with-append")
                    self.assertEqual(
                        [source["path"] for source in record["inputs"]],
                        ["examples/claude-project-rules.md", "examples/claude-append-prompt.md"],
                    )
                    self.assertNotEqual(digest, record["inputs"][0]["sha256"])
                else:
                    self.assertEqual(record["transform"], "copy")
                    self.assertEqual(len(record["inputs"]), 1)
                    self.assertEqual(digest, record["inputs"][0]["sha256"])

    def test_archives_carry_one_prompt_and_its_license_notice(self):
        for tool, manifest in self.manifests.items():
            with self.subTest(tool=tool):
                directory = ROOT / "packs" / manifest["id"]
                archive = packlib.build_zip(directory)
                packlib.check_zip(archive)
                (item,) = manifest["items"]
                with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
                    self.assertEqual(set(zipped.namelist()), {"pack.json", item["file"]})
                    self.assertEqual(zipped.read(item["file"]), (directory / item["file"]).read_bytes())
                    license_info = json.loads(zipped.read("pack.json"))["license"]
                self.assertEqual(license_info["spdx"], "MIT")
                self.assertEqual(len(license_info["notices"]), 1)
                owner = "Ethan" if tool == "zcode" else "Jia-Ethan"
                notice = license_info["notices"][0]
                self.assertIn(f"Copyright (c) 2026 {owner}\n", notice)
                self.assertTrue(notice.startswith("MIT License\n"))
                self.assertIn("Permission is hereby granted, free of charge", notice)
                self.assertIn("shall be included in all", notice)
                self.assertIn('THE SOFTWARE IS PROVIDED "AS IS"', notice)
                self.assertTrue(notice.endswith("SOFTWARE.\n"))

    def test_published_index_lists_the_four_packs_separately(self):
        out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, out, ignore_errors=True)
        base = "https://github.com/Jia-Ethan/keysmith-switch-extensions/releases/download/2026.10.03.1"
        index = packlib.build_index(ROOT / "packs", out, base, "2026-10-03T00:00:00Z")
        entries = {entry["id"]: entry for entry in index["packs"]}
        self.assertEqual(set(entries), set(PACKS.values()))
        for tool, manifest in self.manifests.items():
            entry = entries[PACKS[tool]]
            self.assertEqual(entry["item_count"], 1)
            self.assertEqual(entry["tools"], [tool])
            self.assertEqual(entry["url"], f"{base}/{manifest['id']}-{manifest['version']}.zip")
        self.assertEqual(
            {path.name for path in out.iterdir()},
            {"index.json"} | {f"{m['id']}-{m['version']}.zip" for m in self.manifests.values()},
        )
        packlib.verify_release(out)


if __name__ == "__main__":
    unittest.main()
