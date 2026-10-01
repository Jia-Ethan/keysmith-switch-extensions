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


class OfficialPromptsTest(unittest.TestCase):
    def setUp(self):
        self.directory = ROOT / "packs/keysmith.core"
        self.manifest = packlib.load_pack(self.directory)
        self.sources = json.loads((ROOT / "docs/prompt-sources.json").read_text(encoding="utf-8"))

    def test_one_official_prompt_per_tool_replaces_the_demo(self):
        self.assertFalse((ROOT / "packs/keysmith.example").exists())
        self.assertEqual(set(self.manifest["tools"]), {"codex", "claude", "grok", "zcode"})
        self.assertEqual(len(self.manifest["items"]), 4)
        self.assertEqual(
            {(item["id"], item["tool"]) for item in self.manifest["items"]},
            {(f"{tool}-keysmith", tool) for tool in self.manifest["tools"]},
        )

    def test_prompt_bytes_match_the_recorded_sources(self):
        self.assertEqual(self.sources["pack_id"], self.manifest["id"])
        self.assertEqual(self.sources["pack_version"], self.manifest["version"])
        records = self.sources["prompts"]
        self.assertEqual(len(records), 4)
        self.assertEqual({record["tool"] for record in records}, set(self.manifest["tools"]))
        by_tool = {record["tool"]: record for record in records}
        for item in self.manifest["items"]:
            with self.subTest(tool=item["tool"]):
                record = by_tool[item["tool"]]
                self.assertRegex(record["commit"], r"^[0-9a-f]{40}$")
                self.assertEqual(record["output"], item["file"])
                digest = packlib.sha256_hex((self.directory / item["file"]).read_bytes())
                self.assertEqual(digest, record["sha256"])
                if item["tool"] == "claude":
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

    def test_archive_preserves_all_prompts_and_license_notices(self):
        archive = packlib.build_zip(self.directory)
        packlib.check_zip(archive)
        with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
            expected = {"pack.json"} | {item["file"] for item in self.manifest["items"]}
            self.assertEqual(set(zipped.namelist()), expected)
            for item in self.manifest["items"]:
                self.assertEqual(zipped.read(item["file"]), (self.directory / item["file"]).read_bytes())
            license_info = json.loads(zipped.read("pack.json"))["license"]
        self.assertEqual(license_info["spdx"], "MIT")
        self.assertEqual(len(license_info["notices"]), 2)
        for owner in ("Jia-Ethan", "Ethan"):
            notice = next(text for text in license_info["notices"] if f"Copyright (c) 2026 {owner}\n" in text)
            self.assertTrue(notice.startswith("MIT License\n"))
            self.assertIn("Permission is hereby granted, free of charge", notice)
            self.assertIn("shall be included in all", notice)
            self.assertIn('THE SOFTWARE IS PROVIDED "AS IS"', notice)
            self.assertTrue(notice.endswith("SOFTWARE.\n"))

    def test_published_index_contains_only_the_official_pack(self):
        out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, out, ignore_errors=True)
        base = "https://github.com/Jia-Ethan/keysmith-switch-extensions/releases/download/2026.10.01.2"
        index = packlib.build_index(ROOT / "packs", out, base, "2026-10-01T00:00:00Z")
        self.assertEqual([entry["id"] for entry in index["packs"]], ["keysmith.core"])
        entry = index["packs"][0]
        self.assertEqual(entry["item_count"], 4)
        self.assertEqual(set(entry["tools"]), {"codex", "claude", "grok", "zcode"})
        self.assertEqual(entry["url"], f"{base}/keysmith.core-{self.manifest['version']}.zip")
        self.assertEqual(
            {path.name for path in out.iterdir()},
            {"index.json", f"keysmith.core-{self.manifest['version']}.zip"},
        )
        packlib.verify_release(out)


if __name__ == "__main__":
    unittest.main()
