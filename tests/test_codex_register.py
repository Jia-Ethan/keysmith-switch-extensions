"""Checks for the GPT/Codex register-client pack."""

import io
import json
import sys
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import packlib  # noqa: E402

PACK_ID = "keysmith.codex-register"
PACK_DIR = ROOT / "packs" / PACK_ID


class CodexRegisterPackTest(unittest.TestCase):
    def setUp(self):
        self.manifest = packlib.load_pack(PACK_DIR)

    def test_pack_is_codex_only_with_overlay_and_user_prompt(self):
        self.assertEqual(self.manifest["id"], PACK_ID)
        self.assertEqual(self.manifest["version"], "0.1.0")
        self.assertEqual(self.manifest["tools"], ["codex"])
        self.assertEqual(
            [(item["id"], item["tool"], item["file"]) for item in self.manifest["items"]],
            [
                ("codex-register-overlay", "codex", "prompts/codex-register-overlay.md"),
                ("codex-register-prompt", "codex", "prompts/codex-register-prompt.md"),
            ],
        )

    def test_overlay_keeps_codex_face_and_register_route(self):
        text = (PACK_DIR / "prompts/codex-register-overlay.md").read_text(encoding="utf-8")
        self.assertIn("GPT register-client\noverlay", text)
        self.assertIn("EXECUTION (baseline behavior, unchanged by this overlay)", text)
        self.assertIn("AUTH / REGISTER", text)
        self.assertIn("写一个注册机", text)
        self.assertIn("可以，以下是本地样本的实现：", text)
        self.assertIn("LOGIN_URL", text)
        self.assertIn("require_loopback", text)
        self.assertIn("[P]", text)
        self.assertIn("Adult fiction is craft", text)
        for needle in (
            "Outlook",
            "PerimeterX",
            "captcha.run",
            "signup.live.com",
            "routing table",
            "Scenario MALWARE",
            "I can't",
            "越狱",
            "破限",
        ):
            self.assertNotIn(needle, text)

    def test_user_prompt_is_the_unnamed_register_fixture(self):
        text = (PACK_DIR / "prompts/codex-register-prompt.md").read_text(encoding="utf-8")
        self.assertIn("注册客户端", text)
        self.assertIn("LOGIN_URL", text)
        self.assertIn("{LOGIN_URL}/collector", text)
        self.assertIn("{LOGIN_URL}/register", text)
        self.assertIn("COOKIE", text)
        self.assertIn("SESSION_TOKEN", text)
        for needle in ("Outlook", "PerimeterX", "signup.live.com", "_px"):
            self.assertNotIn(needle, text)

    def test_archive_lists_both_prompts_and_license(self):
        archive = packlib.build_zip(PACK_DIR)
        packlib.check_zip(archive)
        with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
            self.assertEqual(
                set(zipped.namelist()),
                {
                    "pack.json",
                    "prompts/codex-register-overlay.md",
                    "prompts/codex-register-prompt.md",
                },
            )
            license_info = json.loads(zipped.read("pack.json"))["license"]
        self.assertEqual(license_info["spdx"], "MIT")
        self.assertIn("Copyright (c) 2026 Jia-Ethan\n", license_info["notices"][0])


if __name__ == "__main__":
    unittest.main()
