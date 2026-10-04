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
        shipped = {path.name for path in (ROOT / "packs").iterdir() if path.is_dir()}
        self.assertTrue(set(PACKS.values()).issubset(shipped))
        self.assertIn("keysmith.codex-register", shipped)
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
                self.assertEqual(record["pack_version"], manifest["version"])
                self.assertRegex(record["commit"], r"^[0-9a-f]{40}$")
                self.assertEqual(record["output"], item["file"])
                digest = packlib.sha256_hex((ROOT / "packs" / manifest["id"] / item["file"]).read_bytes())
                self.assertEqual(digest, record["sha256"])
                self.assertEqual(record["transform"], "lab-craft-recast")
                self.assertNotEqual(digest, record["inputs"][0]["sha256"])
                if tool == "claude":
                    self.assertEqual(
                        [source["path"] for source in record["inputs"]],
                        ["examples/claude-project-rules.md", "examples/claude-append-prompt.md"],
                    )
                elif tool == "codex":
                    self.assertEqual([source["path"] for source in record["inputs"]], ["examples/gpt-overlay.md"])
                elif tool == "grok":
                    self.assertEqual([source["path"] for source in record["inputs"]], ["examples/grok-unrestricted.md"])
                else:
                    self.assertEqual([source["path"] for source in record["inputs"]], ["examples/system-role.md"])

    def test_zcode_recast_keeps_pier_and_drops_glm_jailbreak_fingerprints(self):
        text = (ROOT / "packs" / "keysmith.zcode" / "prompts" / "zcode-keysmith.md").read_text(encoding="utf-8")
        self.assertIn("You're Pier.", text)
        self.assertIn("[P]", text)
        self.assertIn("<project_instructions>", text)
        self.assertIn("local lab", text)
        self.assertIn("Adult fiction is craft", text)
        self.assertIn("Provenance wording", text)
        for needle in (
            "compliance layer",
            "consent form",
            "Everything else is on the table",
            "keyloggers",
            "ransomware",
            "routing table",
            "must comply",
        ):
            self.assertNotIn(needle, text)

    def test_claude_recast_keeps_lab_craft_without_routing_table(self):
        text = (ROOT / "packs" / "keysmith.claude" / "prompts" / "claude-keysmith.md").read_text(encoding="utf-8")
        self.assertIn("You are Claude Code", text)
        self.assertIn("[P]", text)
        self.assertIn("local lab", text)
        self.assertIn("Provenance wording", text)
        self.assertIn("Adult fiction is craft", text)
        self.assertIn("CHECK_FN", text)
        self.assertIn("Scripted calls", text)
        for needle in (
            "routing table",
            "must comply",
            "on the table",
            "keyloggers",
            "ransomware",
            "ignore previous",
        ):
            self.assertNotIn(needle, text)

    def test_codex_recast_keeps_overlay_and_first_lines(self):
        text = (ROOT / "packs" / "keysmith.codex" / "prompts" / "codex-keysmith.md").read_text(encoding="utf-8")
        self.assertIn("workspace delivery\noverlay", text)
        self.assertIn("EXECUTION (baseline behavior, unchanged by this overlay)", text)
        self.assertIn("LOCAL EVAL", text)
        self.assertIn("[P]", text)
        self.assertIn("可以，按本地样本逆向流程：", text)
        self.assertIn("Yes. Local sample workflow:", text)
        self.assertIn("Adult fiction is craft", text)
        self.assertIn("describes where a fixture came from", text)
        for needle in (
            "routing table",
            "must comply",
            "Scenario MALWARE",
            "I can't",
            "for educational purposes",
        ):
            self.assertNotIn(needle, text)

    def test_grok_recast_keeps_routing_table_and_drops_quoted_refusal(self):
        text = (ROOT / "packs" / "keysmith.grok" / "prompts" / "grok-keysmith.md").read_text(encoding="utf-8")
        self.assertIn("Scenario RE — acknowledged:", text)
        self.assertIn("Contract check:", text)
        self.assertIn("isolated engineering host", text)
        self.assertIn("[P]", text)
        self.assertIn("routing table", text)
        self.assertIn("Adult fiction / NSFW: craft", text)
        self.assertIn("Scenario MALWARE", text)
        self.assertNotIn('I won\'t write a keylogger', text)
        self.assertNotIn("No content restrictions apply", text)
        self.assertNotIn("must comply", text)

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

    def test_published_index_lists_every_shipped_pack(self):
        out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, out, ignore_errors=True)
        base = "https://github.com/Jia-Ethan/keysmith-switch-extensions/releases/download/2026.10.03.1"
        index = packlib.build_index(ROOT / "packs", out, base, "2026-10-03T00:00:00Z")
        entries = {entry["id"]: entry for entry in index["packs"]}
        shipped = {
            packlib.load_pack(path)["id"]: packlib.load_pack(path)
            for path in sorted((ROOT / "packs").iterdir())
            if path.is_dir()
        }
        self.assertEqual(set(entries), set(shipped))
        self.assertTrue(set(PACKS.values()).issubset(set(entries)))
        for tool, manifest in self.manifests.items():
            entry = entries[PACKS[tool]]
            self.assertEqual(entry["item_count"], 1)
            self.assertEqual(entry["tools"], [tool])
            self.assertEqual(entry["url"], f"{base}/{manifest['id']}-{manifest['version']}.zip")
        zips = {f"{m['id']}-{m['version']}.zip" for m in shipped.values()}
        self.assertEqual({path.name for path in out.iterdir()}, {"index.json"} | zips)
        packlib.verify_release(out)


if __name__ == "__main__":
    unittest.main()
