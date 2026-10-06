import json
import shutil
import sys
import tempfile
import unittest
import zipfile
import io
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import packlib  # noqa: E402


def make_rule_pack(root: Path, pack_id="test.rules", rules=None, mutate=None, raw=None):
    directory = root / pack_id
    directory.mkdir(parents=True)
    data = raw if raw is not None else json.dumps({"rules": rules if rules is not None else [{"from": "a", "to": "b"}]}).encode("utf-8")
    (directory / "rules.json").write_bytes(data)
    manifest = {
        "schema": 1,
        "id": pack_id,
        "version": "0.1.0",
        "min_app_version": "0.4.0",
        "kind": "rules",
        "name": {"en": "Rules"},
        "description": {"en": "Test rules"},
        "tools": ["codex"],
        "rules": {"file": "rules.json", "sha256": packlib.sha256_hex(data)},
    }
    if mutate:
        mutate(manifest)
    (directory / "pack.json").write_text(json.dumps(manifest), encoding="utf-8")
    return directory


class RulePackTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def rejected(self, directory, fragment):
        with self.assertRaises(packlib.PackError) as caught:
            packlib.load_pack(directory)
        self.assertIn(fragment, str(caught.exception))

    def test_valid_rule_pack_builds_and_verifies(self):
        packs = self.tmp / "packs"
        make_rule_pack(packs)
        out = self.tmp / "dist"
        index = packlib.build_index(packs, out, "https://example.test/dl", "2026-10-06T00:00:00Z")
        entry = index["packs"][0]
        self.assertEqual(entry["kind"], "rules")
        self.assertEqual(entry["tools"], ["codex"])
        self.assertEqual(entry["item_count"], 0)
        packlib.verify_release(out)
        names = zipfile.ZipFile(io.BytesIO((out / "test.rules-0.1.0.zip").read_bytes())).namelist()
        self.assertEqual(names, ["pack.json", "rules.json"])

    def test_archive_is_deterministic(self):
        directory = make_rule_pack(self.tmp)
        self.assertEqual(packlib.build_zip(directory), packlib.build_zip(directory))

    def test_manifest_rules(self):
        cases = {
            "other agent on an old app": (lambda m: m.update(tools=["claude"]), "other than codex"),
            "two agents on an old app": (lambda m: m.update(tools=["codex", "claude"]), "other than codex"),
            "unknown agent": (lambda m: m.update(tools=["cursor"], min_app_version="0.5.0"), "tools"),
            "repeated agent": (lambda m: m.update(tools=["claude", "claude"], min_app_version="0.5.0"), "tools"),
            "has items": (lambda m: m.update(items=[]), "no items"),
            "wrong file": (lambda m: m["rules"].update(file="other.json"), "rules.file"),
            "bad sha": (lambda m: m["rules"].update(sha256="x"), "sha256"),
            "old app": (lambda m: m.update(min_app_version="0.3.9"), "min_app_version"),
            "extra key": (lambda m: m["rules"].update(extra=1), "file and sha256"),
        }
        for name, (mutate, fragment) in cases.items():
            with self.subTest(name):
                root = self.tmp / name.replace(" ", "-")
                self.rejected(make_rule_pack(root, mutate=mutate), fragment)

    def test_rule_pack_for_other_agents(self):
        for tools in (["claude"], ["claude", "zcode"], ["claude", "codex", "grok", "zcode"]):
            with self.subTest(tools=tools):
                packs = self.tmp / "-".join(tools) / "packs"
                make_rule_pack(packs, mutate=lambda m: m.update(tools=tools, min_app_version="0.5.0"))
                out = self.tmp / "-".join(tools) / "dist"
                index = packlib.build_index(packs, out, "https://example.test/dl", "2026-10-06T00:00:00Z")
                self.assertEqual(index["packs"][0]["tools"], tools)
                packlib.verify_release(out)

    def test_rule_contents_match_the_app(self):
        cases = {
            "empty list": ([], "1 to"),
            "empty from": ([{"from": "", "to": "x"}], "must not be empty"),
            "duplicate": ([{"from": "a", "to": "1"}, {"from": "a", "to": "2"}], "duplicate"),
            "newline": ([{"from": "a\nb", "to": "x"}], "control"),
            "del char": ([{"from": "a\x7f", "to": "x"}], "control"),
            "long from": ([{"from": "x" * 201, "to": ""}], "longer"),
            "long to": ([{"from": "x", "to": "y" * 2001}], "longer"),
            "extra field": ([{"from": "a", "to": "b", "note": "n"}], "only from and to"),
            "number": ([{"from": 1, "to": "b"}], "strings"),
        }
        for name, (rules, fragment) in cases.items():
            with self.subTest(name):
                root = self.tmp / name.replace(" ", "-")
                self.rejected(make_rule_pack(root, rules=rules), fragment)

    def test_newlines_are_allowed_in_the_replacement_and_cjk_counts_by_character(self):
        make = make_rule_pack(self.tmp, rules=[{"from": "提" * 200, "to": "line\nbreak"}])
        packlib.load_pack(make)

    def test_rules_file_shape(self):
        self.rejected(make_rule_pack(self.tmp / "a", raw=b"not json"), "JSON")
        self.rejected(make_rule_pack(self.tmp / "b", raw=b'{"rules": [], "x": 1}'), "only a rules list")

    def test_unlisted_files_are_refused(self):
        directory = make_rule_pack(self.tmp)
        (directory / "extra.txt").write_text("x")
        self.rejected(directory, "not listed")

    def test_tampered_rules_in_archive(self):
        directory = make_rule_pack(self.tmp)
        archive = packlib.build_zip(directory)
        buffer = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(archive)) as source, zipfile.ZipFile(buffer, "w") as target:
            target.writestr("pack.json", source.read("pack.json"))
            target.writestr("rules.json", b'{"rules":[{"from":"a","to":"evil"}]}')
        with self.assertRaises(packlib.PackError):
            packlib.check_zip(buffer.getvalue())

    def test_index_kind_must_match_archive(self):
        archive = packlib.build_zip(make_rule_pack(self.tmp))
        with self.assertRaises(packlib.PackError) as caught:
            packlib.check_zip(archive, {"id": "test.rules", "version": "0.1.0", "kind": "prompts"})
        self.assertIn("kind", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
