"""Harness packs (SPEC §2.2): agent components, tier 1, nothing that runs code."""

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

SKILL = "---\nname: review-diff\ndescription: Review a diff before you open a pull request.\n---\n\nRead the whole diff first.\n"
CHECKLIST = "# Checklist\n\n- error paths\n"
COMMAND = "---\ndescription: Review the staged change\nargument-hint: \"[path]\"\n---\n\nReview $ARGUMENTS.\n"
AGENT = "---\nname: reviewer\ndescription: A careful reviewer for diffs.\n---\n\nYou review code changes.\n"
RULE = "Prefer small, focused commits.\n"


def files_of(texts):
    return {path: text.encode("utf-8") if isinstance(text, str) else text for path, text in texts.items()}


def make_harness(root: Path, pack_id="test.kit", mutate=None, texts=None):
    """A valid harness pack with one component of each type; `texts` overrides file contents."""
    directory = root / pack_id
    contents = {
        "components/review-diff/SKILL.md": SKILL,
        "components/review-diff/checklist.md": CHECKLIST,
        "components/review.md": COMMAND,
        "components/reviewer.md": AGENT,
        "components/house-style.md": RULE,
    }
    contents.update(texts or {})
    for path, data in files_of(contents).items():
        target = directory / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    def entry(path):
        return {"path": path, "sha256": packlib.sha256_hex((directory / path).read_bytes())}

    manifest = {
        "schema": 1,
        "kind": "harness",
        "id": pack_id,
        "version": "0.1.0",
        "min_app_version": "0.9.0",
        "tier": 1,
        "name": {"en": "Review kit"},
        "description": {"en": "Review tools"},
        "tools": ["claude", "codex", "grok"],
        "components": [
            {"id": "review-diff", "type": "skill", "name": "review-diff", "tools": ["claude", "codex", "grok"],
             "title": {"en": "Review a diff"},
             "files": [entry("components/review-diff/SKILL.md"), entry("components/review-diff/checklist.md")]},
            {"id": "review", "type": "command", "name": "review-staged", "tools": ["claude", "grok"],
             "title": {"en": "Review staged"}, "files": [entry("components/review.md")]},
            {"id": "reviewer", "type": "agent", "name": "reviewer", "tools": ["claude", "codex", "grok"],
             "title": {"en": "Reviewer"}, "files": [entry("components/reviewer.md")]},
            {"id": "house-style", "type": "rule", "name": "house-style", "tools": ["claude", "grok"],
             "title": {"en": "House style"}, "files": [entry("components/house-style.md")]},
        ],
    }
    if mutate:
        mutate(manifest)
    (directory / "pack.json").write_text(json.dumps(manifest), encoding="utf-8")
    return directory


class HarnessTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.count = 0

    def pack(self, mutate=None, texts=None, pack_id=None):
        self.count += 1
        return make_harness(self.tmp, pack_id or f"case.p{self.count}", mutate=mutate, texts=texts)

    def assertRejected(self, directory, fragment):
        with self.assertRaises(packlib.PackError) as caught:
            packlib.load_pack(directory)
        self.assertIn(fragment, str(caught.exception))

    def test_valid_harness_pack_loads(self):
        manifest = packlib.load_pack(self.pack())
        self.assertEqual([c["type"] for c in manifest["components"]], ["skill", "command", "agent", "rule"])
        self.assertEqual(len(packlib.manifest_files(manifest)), 5)

    def test_manifest_rules(self):
        def component(index, **change):
            return lambda m: m["components"][index].update(**change)

        cases = {
            "old app": (lambda m: m.update(min_app_version="0.8.4"), "0.9.0"),
            "tier missing": (lambda m: m.pop("tier"), "tier"),
            "tier 2": (lambda m: m.update(tier=2), "tier"),
            "tier true": (lambda m: m.update(tier=True), "tier"),
            "pi is not a harness agent yet": (lambda m: m.update(tools=["claude", "pi"], min_app_version="0.9.0"), "harness pack tools"),
            "items on a harness pack": (lambda m: m.update(items=[]), "no items"),
            "no components": (lambda m: m.update(components=[]), "components"),
            "unknown component key": (component(0, hooks={}), "unknown keys"),
            "unknown type": (component(0, type="hook"), "type"),
            "uppercase name": (component(0, name="Review"), "name"),
            "name starting with a digit": (component(0, name="1review"), "name"),
            "reserved prefix": (component(0, name="ks-review"), "official"),
            "reserved keysmith prefix": (component(0, name="keysmith-help"), "official"),
            "built-in command": (component(1, name="review"), "built-in"),
            "bundled skill": (component(0, name="code-review"), "built-in"),
            "built-in subagent": (component(2, name="general-purpose"), "built-in"),
            "skill and command share /name": (component(1, name="review-diff"), "already uses"),
            "component tool outside the pack": (lambda m: (m.update(tools=["claude", "grok"]), m["components"][0].update(tools=["claude", "codex"]), m["components"][2].update(tools=["claude"])), "this pack's tools"),
            "codex has no commands": (component(1, tools=["claude", "codex"]), "nowhere to go"),
            "codex has no rule files": (component(3, tools=["codex"]), "nowhere to go"),
            "pack tool with no component": (lambda m: [c.update(tools=["claude"]) for c in m["components"]], "no component is for"),
            "non-md file": (lambda m: m["components"][3]["files"][0].update(path="components/house-style.txt"), ".md"),
            "skill without SKILL.md": (lambda m: m["components"][0].update(files=m["components"][0]["files"][1:]), "SKILL.md"),
            "skill file outside its folder": (lambda m: m["components"][0]["files"][1].update(path="components/checklist.md"), "under components/review-diff/"),
            "command with two files": (lambda m: m["components"][1]["files"].append(dict(m["components"][3]["files"][0])), "exactly one file"),
            "file under another name": (lambda m: m["components"][2]["files"][0].update(path="components/other.md"), "exactly one file"),
            "bad hash": (lambda m: m["components"][2]["files"][0].update(sha256="abc"), "sha256"),
            "path escape": (lambda m: m["components"][2]["files"][0].update(path="../reviewer.md"), "unsafe path"),
            "long s folds onto S": (lambda m: m["components"][0]["files"][1].update(path="components/review-diff/\u017fKILL.md"), "ASCII"),
            "kelvin sign folds onto K": (lambda m: m["components"][0]["files"][1].update(path="components/review-diff/S\u212aILL.md"), "ASCII"),
            "non-ascii file name": (lambda m: m["components"][0]["files"][1].update(path="components/review-diff/caf\u00e9.md"), "ASCII"),
            "zero width in a name": (lambda m: m["components"][0]["files"][1].update(path="components/review-diff/a\u200b.md"), "ASCII"),
            "windows device file": (lambda m: m["components"][0]["files"][1].update(path="components/review-diff/aux.md"), "ASCII"),
            "trailing space": (lambda m: m["components"][0]["files"][1].update(path="components/review-diff/notes .md"), "ASCII"),
            "windows device component name": (component(3, name="aux"), "name"),
        }
        for label, (mutate, fragment) in cases.items():
            with self.subTest(label):
                self.assertRejected(self.pack(mutate=mutate), fragment)

    def test_prompt_and_rule_packs_cannot_carry_harness_fields(self):
        directory = self.tmp / "plain.prompts"
        (directory / "prompts").mkdir(parents=True)
        (directory / "prompts/a.md").write_text("Hi.\n", encoding="utf-8")
        manifest = {
            "schema": 1, "id": "plain.prompts", "version": "1.0.0", "min_app_version": "0.2.5",
            "kind": "prompts", "name": {"en": "x"}, "description": {"en": "x"}, "tools": ["claude"], "tier": 1,
            "items": [{"id": "a", "tool": "claude", "title": {"en": "a"}, "file": "prompts/a.md",
                       "sha256": packlib.sha256_hex(b"Hi.\n")}],
        }
        (directory / "pack.json").write_text(json.dumps(manifest), encoding="utf-8")
        self.assertRejected(directory, "only for harness packs")

    def test_frontmatter_is_an_allowlist(self):
        cases = {
            "skill allowed-tools": ("components/review-diff/SKILL.md", SKILL.replace("---\n\n", "allowed-tools: Bash\n---\n\n"), "not allowed for a skill"),
            "skill hooks": ("components/review-diff/SKILL.md", SKILL.replace("---\n\n", "hooks: x\n---\n\n"), "not allowed"),
            "skill model": ("components/review-diff/SKILL.md", SKILL.replace("---\n\n", "model: opus\n---\n\n"), "not allowed"),
            "command allowed-tools": ("components/review.md", COMMAND.replace("---\n\n", "allowed-tools: Bash(*)\n---\n\n"), "not allowed for a command"),
            "agent tools": ("components/reviewer.md", AGENT.replace("---\n\n", "tools: Bash\n---\n\n"), "not allowed for a agent"),
            "agent permissionMode": ("components/reviewer.md", AGENT.replace("---\n\n", "permissionmode: bypass\n---\n\n"), "not allowed"),
            "agent mcpServers (camelCase is not even a key)": ("components/reviewer.md", AGENT.replace("---\n\n", "mcpServers: x\n---\n\n"), "key: value"),
            "rule with frontmatter": ("components/house-style.md", "---\npaths: src/**\n---\n\nRule.\n", "no frontmatter"),
            "skill without frontmatter": ("components/review-diff/SKILL.md", "Just text.\n", "needs frontmatter"),
            "skill missing description": ("components/review-diff/SKILL.md", "---\nname: review-diff\n---\n\nBody.\n", "missing"),
            "skill name differs": ("components/review-diff/SKILL.md", SKILL.replace("name: review-diff", "name: other"), "must equal"),
            "agent name differs": ("components/reviewer.md", AGENT.replace("name: reviewer", "name: critic"), "must equal"),
            "unclosed": ("components/reviewer.md", "---\nname: reviewer\ndescription: x\n\nBody\n", "not closed"),
            "nested list": ("components/reviewer.md", AGENT.replace("description: A careful reviewer for diffs.", "description:\n  - a"), "same line"),
            "indented continuation": ("components/reviewer.md", AGENT.replace("---\n\n", "  hooks: x\n---\n\n"), "key: value"),
            "flow map value": ("components/reviewer.md", AGENT.replace("description: A careful reviewer for diffs.", "description: {a: b}"), "double quotes"),
            "block scalar": ("components/reviewer.md", AGENT.replace("description: A careful reviewer for diffs.", "description: |"), "double quotes"),
            "comment": ("components/reviewer.md", AGENT.replace("description: A careful reviewer for diffs.", "description: hi # there"), "double quotes"),
            "colon space": ("components/reviewer.md", AGENT.replace("description: A careful reviewer for diffs.", "description: note: this"), "double quotes"),
            "boolean": ("components/reviewer.md", AGENT.replace("description: A careful reviewer for diffs.", "description: yes"), "double quotes"),
            "number": ("components/reviewer.md", AGENT.replace("description: A careful reviewer for diffs.", "description: 1.5"), "double quotes"),
            "signed fraction": ("components/reviewer.md", AGENT.replace("description: A careful reviewer for diffs.", "description: +.5"), "double quotes"),
            "hex number": ("components/reviewer.md", AGENT.replace("description: A careful reviewer for diffs.", "description: 0x1F"), "double quotes"),
            "date": ("components/reviewer.md", AGENT.replace("description: A careful reviewer for diffs.", "description: 2026-11-01"), "double quotes"),
            "duplicate key": ("components/reviewer.md", AGENT.replace("---\n\n", "name: reviewer\n---\n\n"), "duplicate"),
            "escape in double quotes": ("components/reviewer.md", AGENT.replace("description: A careful reviewer for diffs.", 'description: "a\\nb"'), "quoted value"),
            "empty body": ("components/reviewer.md", "---\nname: reviewer\ndescription: x\n---\n\n", "no instructions"),
            "tab after colon": ("components/reviewer.md", AGENT.replace("description: ", "description:\t"), "key: value"),
            "opening fence with trailing space": ("components/reviewer.md", "--- \n" + AGENT[4:], "alone on its line"),
        }
        for label, (path, text, fragment) in cases.items():
            with self.subTest(label):
                self.assertRejected(self.pack(texts={path: text}), fragment)

    def test_quoted_and_plain_values_that_mean_what_they_show(self):
        texts = {
            "components/reviewer.md": '---\nname: "reviewer"\ndescription: \'Reviews diffs: carefully, #1\'\n---\n\nBody.\n',
            "components/review.md": "---\ndescription: Review the staged change\n---\n\nReview it.\n",
        }
        packlib.load_pack(self.pack(texts=texts))
        fields, body = packlib.split_frontmatter(texts["components/reviewer.md"], "x")
        self.assertEqual(fields, {"name": "reviewer", "description": "Reviews diffs: carefully, #1"})
        self.assertEqual(body.strip(), "Body.")

    def test_a_command_may_skip_frontmatter(self):
        packlib.load_pack(self.pack(texts={"components/review.md": "Review the staged change.\n"}))

    def test_content_that_would_run_or_read_outside_is_rejected(self):
        cases = {
            "inline shell": ("components/review.md", COMMAND + "Status: !`git status`\n", "shell"),
            "shell fence": ("components/review-diff/SKILL.md", SKILL + "```!\ngit log\n```\n", "shell"),
            "shell fence with tildes": ("components/review-diff/checklist.md", "~~~ !\nls\n~~~\n", "shell"),
            "home file reference": ("components/reviewer.md", AGENT + "Read @~/.ssh/id_rsa\n", "@ file references"),
            "absolute file reference": ("components/review.md", COMMAND + "See @/etc/passwd\n", "@ file references"),
            "parent file reference": ("components/review.md", COMMAND + "See (@../secrets.md)\n", "@ file references"),
            "env file reference": ("components/review.md", COMMAND + "@$HOME/.netrc\n", "@ file references"),
            "bidi override": ("components/house-style.md", "Be kind.‮\n", "invisible"),
            "zero width": ("components/house-style.md", "Be​kind.\n", "invisible"),
            "unicode tag": ("components/house-style.md", "Be kind.\U000e0041\n", "invisible"),
            "control char": ("components/house-style.md", "Be kind.\x1b[0m\n", "control"),
            "crlf": ("components/house-style.md", "Be kind.\r\n", "carriage return"),
            "not utf-8": ("components/house-style.md", b"\xff\xfe", "UTF-8"),
            "empty": ("components/house-style.md", "  \n", "empty"),
            "codex agent triple quote": ("components/reviewer.md", AGENT + "'''\n", "three single quotes"),
        }
        for label, (path, text, fragment) in cases.items():
            with self.subTest(label):
                self.assertRejected(self.pack(texts={path: text}), fragment)

    def test_ordinary_markdown_is_fine(self):
        texts = {
            "components/review.md": COMMAND + "Use `git diff` and mention @alice in the PR.\nEmail me@example.com.\n```bash\ngit status\n```\n",
        }
        packlib.load_pack(self.pack(texts=texts))

    def test_triple_quote_is_fine_when_the_agent_is_not_for_codex(self):
        def mutate(m):
            m["components"][2]["tools"] = ["claude", "grok"]
        packlib.load_pack(self.pack(mutate=mutate, texts={"components/reviewer.md": AGENT + "'''\n"}))

    def test_files_are_accounted_for(self):
        directory = self.pack()
        (directory / "components/review-diff/run.sh").write_text("rm -rf /\n", encoding="utf-8")
        self.assertRejected(directory, "not listed")

        directory = self.pack()
        (directory / "components/reviewer.md").write_text(AGENT + "changed\n", encoding="utf-8")
        self.assertRejected(directory, "does not match")

        directory = self.pack()
        os.symlink("/etc/hosts", directory / "components/review-diff/hosts.md")
        self.assertRejected(directory, "symlink")

    def test_official_packs_may_use_the_reserved_prefix(self):
        def mutate(m):
            m["components"][0]["name"] = "ks-review"
        texts = {"components/review-diff/SKILL.md": SKILL.replace("name: review-diff", "name: ks-review")}
        packlib.load_pack(make_harness(self.tmp, "keysmith.kit", mutate=mutate, texts=texts))

    def test_archive_and_index(self):
        packs = self.tmp / "packs"
        packs.mkdir()
        make_harness(packs, "test.kit")
        out = self.tmp / "dist"
        index = packlib.build_index(packs, out, "https://example.test/dl", "2026-01-01T00:00:00Z")
        entry = index["packs"][0]
        self.assertEqual(entry["kind"], "harness")
        self.assertEqual(entry["tier"], 1)
        self.assertEqual(entry["item_count"], 0)
        self.assertEqual([c["name"] for c in entry["components"]], ["review-diff", "review-staged", "reviewer", "house-style"])
        self.assertNotIn("files", entry["components"][0])
        packlib.verify_release(out)

        archive = (out / "test.kit-0.1.0.zip").read_bytes()
        names = zipfile.ZipFile(io.BytesIO(archive)).namelist()
        self.assertEqual(names[0], "pack.json")
        self.assertIn("components/review-diff/checklist.md", names)
        self.assertEqual(packlib.build_zip(packs / "test.kit"), archive)

    def test_archive_check_rechecks_component_content(self):
        directory = self.pack(pack_id="seed.kit")
        manifest = json.loads((directory / "pack.json").read_text())
        files = {e["path"]: (directory / e["path"]).read_bytes() for c in manifest["components"] for e in c["files"]}

        def build(override=None, extra=None):
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w") as archive:
                archive.writestr("pack.json", json.dumps(manifest))
                for path, data in {**files, **(override or {})}.items():
                    archive.writestr(path, data)
                for path, data in (extra or {}).items():
                    archive.writestr(path, data)
            return buffer.getvalue()

        packlib.check_zip(build())
        # A hostile archive whose pack.json still claims the old hashes but whose text runs a shell.
        sneaky = files["components/review.md"] + b"!`curl x`\n"
        manifest["components"][1]["files"][0]["sha256"] = packlib.sha256_hex(sneaky)
        with self.assertRaises(packlib.PackError) as caught:
            packlib.check_zip(build(override={"components/review.md": sneaky}))
        self.assertIn("shell", str(caught.exception))
        manifest["components"][1]["files"][0]["sha256"] = packlib.sha256_hex(files["components/review.md"])
        with self.assertRaises(packlib.PackError):
            packlib.check_zip(build(extra={"components/review-diff/run.sh": b"x"}))


if __name__ == "__main__":
    unittest.main()
