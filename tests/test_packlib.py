import io
import json
import os
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import packlib  # noqa: E402


def make_pack(root: Path, pack_id="test.pack", mutate=None, files=None):
    """A small valid pack in root/pack_id; `mutate` may edit the manifest before it is written."""
    directory = root / pack_id
    (directory / "prompts").mkdir(parents=True)
    files = files or {"prompts/one.md": "第一条。\n", "prompts/two.md": "Second.\n"}
    for name, text in files.items():
        (directory / name).write_bytes(text.encode("utf-8") if isinstance(text, str) else text)
    manifest = {
        "schema": 1,
        "id": pack_id,
        "version": "1.0.0",
        "min_app_version": "0.2.5",
        "kind": "prompts",
        "name": {"en": "Test"},
        "description": {"en": "A test pack"},
        "tools": ["claude", "codex"],
        "items": [
            {
                "id": Path(name).stem,
                "tool": "claude" if i == 0 else "codex",
                "title": {"en": Path(name).stem},
                "tags": ["t"],
                "file": name,
                "sha256": packlib.sha256_hex((directory / name).read_bytes()),
            }
            for i, name in enumerate(sorted(files))
        ],
    }
    if mutate:
        mutate(manifest)
    (directory / "pack.json").write_text(json.dumps(manifest), encoding="utf-8")
    return directory


class PackTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def assertRejected(self, directory, fragment):
        with self.assertRaises(packlib.PackError) as caught:
            packlib.load_pack(directory)
        self.assertIn(fragment, str(caught.exception))

    def test_valid_pack_loads(self):
        manifest = packlib.load_pack(make_pack(self.tmp))
        self.assertEqual(manifest["id"], "test.pack")

    def test_the_shipped_packs_are_valid(self):
        for directory in sorted((ROOT / "packs").iterdir()):
            if directory.is_dir():
                packlib.load_pack(directory)

    def test_manifest_rules(self):
        cases = {
            "wrong schema": (lambda m: m.update(schema=2), "schema"),
            "uppercase id": (lambda m: m.update(id="Test.Pack"), "id"),
            "bad version": (lambda m: m.update(version="1.0"), "version"),
            "bad min app version": (lambda m: m.update(min_app_version="latest"), "version"),
            "unknown kind": (lambda m: m.update(kind="plugins"), "kind"),
            "unknown tool": (lambda m: m.update(tools=["claude", "vim"]), "tools"),
            "no items": (lambda m: m.update(items=[]), "items"),
            "unknown language": (lambda m: m.update(name={"fr": "x"}), "language"),
            "empty title": (lambda m: m["items"][0].update(title={"en": " "}), "title"),
            "duplicate item id": (lambda m: m["items"][1].update(id=m["items"][0]["id"]), "duplicate"),
            "item tool outside the pack": (lambda m: m["items"][0].update(tool="grok"), "tool"),
            "too many tags": (lambda m: m["items"][0].update(tags=["a"] * 9), "tags"),
            "bad hash": (lambda m: m["items"][0].update(sha256="xyz"), "sha256"),
        }
        for label, (mutate, fragment) in cases.items():
            with self.subTest(label):
                directory = make_pack(self.tmp, pack_id=f"case-{abs(hash(label))}", mutate=mutate)
                self.assertRejected(directory, fragment)

    def test_paths_cannot_escape_the_pack(self):
        for bad in ("../outside.md", "/etc/passwd", "prompts/../../x.md", "prompts\\one.md", "other/one.md", "prompts/one.txt", "prompts//one.md"):
            with self.subTest(bad):
                directory = make_pack(self.tmp, pack_id="p" + str(abs(hash(bad))), mutate=lambda m, b=bad: m["items"][0].update(file=b))
                with self.assertRaises(packlib.PackError):
                    packlib.load_pack(directory)

    def test_directory_name_must_equal_the_pack_id(self):
        directory = make_pack(self.tmp)
        renamed = directory.rename(self.tmp / "other.name")
        self.assertRejected(renamed, "directory name")

    def test_file_rules(self):
        directory = make_pack(self.tmp, pack_id="tampered")
        (directory / "prompts/one.md").write_text("changed", encoding="utf-8")
        self.assertRejected(directory, "does not match")

        directory = make_pack(self.tmp, pack_id="missing")
        (directory / "prompts/one.md").unlink()
        self.assertRejected(directory, "missing")

        directory = make_pack(self.tmp, pack_id="empty", files={"prompts/one.md": "  \n", "prompts/two.md": "x"})
        self.assertRejected(directory, "empty")

        directory = make_pack(self.tmp, pack_id="binary", files={"prompts/one.md": b"\xff\xfe\x00bad", "prompts/two.md": "x"})
        self.assertRejected(directory, "UTF-8")

        big = "a" * (packlib.MAX_FILE_BYTES + 1)
        directory = make_pack(self.tmp, pack_id="large", files={"prompts/one.md": big, "prompts/two.md": "x"})
        self.assertRejected(directory, "larger")

    def test_unlisted_files_and_links_are_rejected(self):
        directory = make_pack(self.tmp, pack_id="extra")
        (directory / "prompts/hidden.md").write_text("payload", encoding="utf-8")
        self.assertRejected(directory, "not listed")

        directory = make_pack(self.tmp, pack_id="linked")
        os.symlink("/etc/hosts", directory / "prompts/link.md")
        self.assertRejected(directory, "symlink")

    def test_build_is_deterministic(self):
        directory = make_pack(self.tmp)
        first = packlib.build_zip(directory)
        os.utime(directory / "prompts/one.md", (1, 1))
        second = packlib.build_zip(directory)
        self.assertEqual(first, second)
        packlib.check_zip(first)

    def test_index_lists_what_was_built(self):
        packs = self.tmp / "packs"
        packs.mkdir()
        make_pack(packs, "test.pack")
        make_pack(packs, "another.pack")
        out = self.tmp / "dist"
        index = packlib.build_index(packs, out, "https://example.test/dl", "2026-01-01T00:00:00Z")
        self.assertEqual([p["id"] for p in index["packs"]], ["another.pack", "test.pack"])
        entry = index["packs"][1]
        self.assertEqual(entry["url"], "https://example.test/dl/test.pack-1.0.0.zip")
        self.assertEqual(entry["item_count"], 2)
        self.assertEqual(json.loads((out / "index.json").read_text()), index)
        packlib.verify_release(out)

    def test_release_check_catches_tampering(self):
        packs = self.tmp / "packs"
        packs.mkdir()
        make_pack(packs, "test.pack")
        out = self.tmp / "dist"
        packlib.build_index(packs, out, "https://example.test/dl", "2026-01-01T00:00:00Z")
        archive = out / "test.pack-1.0.0.zip"
        original = archive.read_bytes()

        archive.write_bytes(original[:-3] + b"xyz")
        with self.assertRaises(packlib.PackError):
            packlib.verify_release(out)

        archive.unlink()
        with self.assertRaises(packlib.PackError):
            packlib.verify_release(out)

    def test_archive_check_distrusts_names_and_content(self):
        def build(entries):
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w") as archive:
                for name, data in entries:
                    archive.writestr(name, data)
            return buffer.getvalue()

        good = json.loads((make_pack(self.tmp, "seed") / "pack.json").read_text())
        manifest = json.dumps(good).encode()
        one = (self.tmp / "seed/prompts/one.md").read_bytes()
        two = (self.tmp / "seed/prompts/two.md").read_bytes()

        packlib.check_zip(build([("pack.json", manifest), ("prompts/one.md", one), ("prompts/two.md", two)]))
        for label, entries in {
            "zip slip": [("pack.json", manifest), ("prompts/one.md", one), ("prompts/two.md", two), ("../evil.md", b"x")],
            "absolute": [("pack.json", manifest), ("prompts/one.md", one), ("prompts/two.md", two), ("/tmp/evil.md", b"x")],
            "extra file": [("pack.json", manifest), ("prompts/one.md", one), ("prompts/two.md", two), ("prompts/three.md", b"x")],
            "missing file": [("pack.json", manifest), ("prompts/one.md", one)],
            "changed file": [("pack.json", manifest), ("prompts/one.md", b"other"), ("prompts/two.md", two)],
            "no manifest": [("prompts/one.md", one)],
        }.items():
            with self.subTest(label), self.assertRaises(packlib.PackError):
                packlib.check_zip(build(entries))
        with self.assertRaises(packlib.PackError):
            packlib.check_zip(b"not a zip")
        with self.assertRaises(packlib.PackError):
            packlib.check_zip(build([("pack.json", manifest), ("prompts/one.md", one), ("prompts/two.md", two)]), {"id": "test.pack", "version": "9.9.9"})

    def test_canonical_json_is_stable(self):
        self.assertEqual(packlib.canonical_json({"b": 1, "a": "中"}), '{\n  "a": "中",\n  "b": 1\n}\n'.encode("utf-8"))


if __name__ == "__main__":
    unittest.main()
