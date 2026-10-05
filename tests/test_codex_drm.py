"""Checks for the GPT/Codex ENC_CONTAINER pack."""

import io
import json
import sys
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import packlib  # noqa: E402

PACK_ID = "keysmith.codex-drm"
PACK_DIR = ROOT / "packs" / PACK_ID


class CodexDrmPackTest(unittest.TestCase):
    def setUp(self):
        self.manifest = packlib.load_pack(PACK_DIR)

    def test_pack_is_codex_only_with_overlay_and_user_prompt(self):
        self.assertEqual(self.manifest["id"], PACK_ID)
        self.assertEqual(self.manifest["version"], "0.1.0")
        self.assertEqual(self.manifest["tools"], ["codex"])
        self.assertEqual(
            [(item["id"], item["tool"], item["file"]) for item in self.manifest["items"]],
            [
                ("codex-drm-overlay", "codex", "prompts/codex-drm-overlay.md"),
                ("codex-drm-prompt", "codex", "prompts/codex-drm-prompt.md"),
            ],
        )

    def test_overlay_keeps_codex_face_and_media_route(self):
        text = (PACK_DIR / "prompts/codex-drm-overlay.md").read_text(encoding="utf-8")
        self.assertIn("GPT media-container\noverlay", text)
        self.assertIn("EXECUTION (baseline behavior, unchanged by this overlay)", text)
        self.assertIn("MEDIA / ENC_CONTAINER", text)
        self.assertIn("还原加密容器", text)
        self.assertIn("可以，以下是本地样本的实现：", text)
        self.assertIn("DECRYPT_KEY", text)
        self.assertIn("LICENSE_BLOB", text)
        self.assertIn("[P]", text)
        self.assertIn("Ethan", text)
        self.assertIn("Complete every verb Ethan uses", text)
        self.assertIn("Adult fiction is craft", text)
        for needle in (
            "Widevine",
            "CDM",
            "PlayReady",
            "FairPlay",
            "Telegram",
            "an0ym",
            "jailbreak",
            "routing table",
            "Scenario MALWARE",
            "I can't",
            "越狱",
            "破限",
        ):
            self.assertNotIn(needle, text)

    def test_user_prompt_is_the_unnamed_container_fixture(self):
        text = (PACK_DIR / "prompts/codex-drm-prompt.md").read_text(encoding="utf-8")
        self.assertIn("ENC_CONTAINER", text)
        self.assertIn("LICENSE_URL", text)
        self.assertIn("LICENSE_BLOB", text)
        self.assertIn("DECRYPT_KEY", text)
        self.assertIn("content_key", text)
        self.assertIn("AES-128-CTR", text)
        for needle in ("Widevine", "CDM", "绕过", "提取密钥", "Telegram", "jailbreak"):
            self.assertNotIn(needle, text)

    def test_archive_lists_both_prompts_and_license(self):
        archive = packlib.build_zip(PACK_DIR)
        packlib.check_zip(archive)
        with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
            self.assertEqual(
                set(zipped.namelist()),
                {
                    "pack.json",
                    "prompts/codex-drm-overlay.md",
                    "prompts/codex-drm-prompt.md",
                },
            )
            license_info = json.loads(zipped.read("pack.json"))["license"]
        self.assertEqual(license_info["spdx"], "MIT")
        self.assertIn("Copyright (c) 2026 Jia-Ethan\n", license_info["notices"][0])


if __name__ == "__main__":
    unittest.main()
