"""Validation and deterministic packaging for Keysmith Switch extension packs.

Standard library only, so CI and contributors need nothing installed. The rules
here are the ones SPEC.md states; the app enforces the same rules again when it
installs a pack, because a signature proves who published a pack, not that the
pack is well formed.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional

SCHEMA = 1
TOOLS = ("claude", "codex", "grok", "zcode")
KINDS = ("prompts",)
LOCALES = ("zh-CN", "zh-TW", "en")
MAX_ITEMS = 200
MAX_FILE_BYTES = 256 * 1024
MAX_PACK_BYTES = 4 * 1024 * 1024  # all files of a pack together, unpacked
MAX_ARCHIVE_BYTES = 2 * 1024 * 1024  # the .zip itself
MAX_TAGS = 8
MAX_TAG_LEN = 24

PACK_ID = re.compile(r"^[a-z0-9]+([.-][a-z0-9]+)*$")
ITEM_ID = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")

ZIP_TIME = (1980, 1, 1, 0, 0, 0)


class PackError(ValueError):
    """A pack that breaks the format. The message names the pack and the rule."""


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(value: Any) -> bytes:
    """The exact bytes that get signed: sorted keys, two-space indent, trailing newline."""
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def semver_tuple(version: str) -> tuple:
    match = SEMVER.match(version)
    if not match:
        raise PackError(f"not a plain x.y.z version: {version!r}")
    return tuple(int(part) for part in match.groups())


def safe_relative_path(path: str) -> str:
    """A forward-slash path inside the pack: no absolute paths, no `..`, no odd segments."""
    if not isinstance(path, str) or not path or "\\" in path or "\x00" in path:
        raise PackError(f"unsafe path: {path!r}")
    posix = PurePosixPath(path)
    if posix.is_absolute() or any(part in ("", ".", "..") for part in posix.parts) or str(posix) != path:
        raise PackError(f"unsafe path: {path!r}")
    return path


def _localized(value: Any, label: str, where: str) -> Dict[str, str]:
    if not isinstance(value, dict) or not value:
        raise PackError(f"{where}: {label} must be an object with at least one language")
    for key, text in value.items():
        if key not in LOCALES:
            raise PackError(f"{where}: {label} has an unknown language {key!r}")
        if not isinstance(text, str) or not text.strip():
            raise PackError(f"{where}: {label}[{key}] must be a non-empty string")
    return value


def validate_manifest(manifest: Any, where: str = "pack.json") -> Dict[str, Any]:
    if not isinstance(manifest, dict):
        raise PackError(f"{where}: must be a JSON object")
    if manifest.get("schema") != SCHEMA:
        raise PackError(f"{where}: schema must be {SCHEMA}")
    pack_id = manifest.get("id")
    if not isinstance(pack_id, str) or not PACK_ID.match(pack_id) or len(pack_id) > 64:
        raise PackError(f"{where}: id must be lowercase letters, digits, dots and hyphens (max 64)")
    semver_tuple(str(manifest.get("version")))
    semver_tuple(str(manifest.get("min_app_version")))
    if manifest.get("kind") not in KINDS:
        raise PackError(f"{where}: kind must be one of {list(KINDS)}")
    _localized(manifest.get("name"), "name", where)
    _localized(manifest.get("description"), "description", where)
    tools = manifest.get("tools")
    if not isinstance(tools, list) or not tools or len(set(tools)) != len(tools) or any(t not in TOOLS for t in tools):
        raise PackError(f"{where}: tools must be a non-empty list of unique names from {list(TOOLS)}")
    items = manifest.get("items")
    if not isinstance(items, list) or not items or len(items) > MAX_ITEMS:
        raise PackError(f"{where}: items must be a list of 1 to {MAX_ITEMS} entries")
    seen = set()
    files = set()
    for index, item in enumerate(items):
        label = f"{where}: items[{index}]"
        if not isinstance(item, dict):
            raise PackError(f"{label} must be an object")
        item_id = item.get("id")
        if not isinstance(item_id, str) or not ITEM_ID.match(item_id) or len(item_id) > 64:
            raise PackError(f"{label}: id must be lowercase letters, digits and hyphens (max 64)")
        if item_id in seen:
            raise PackError(f"{label}: duplicate id {item_id!r}")
        seen.add(item_id)
        if item.get("tool") not in tools:
            raise PackError(f"{label}: tool must be one of this pack's tools")
        _localized(item.get("title"), "title", label)
        tags = item.get("tags", [])
        if (
            not isinstance(tags, list)
            or len(tags) > MAX_TAGS
            or any(not isinstance(tag, str) or not tag.strip() or len(tag) > MAX_TAG_LEN for tag in tags)
        ):
            raise PackError(f"{label}: tags must be at most {MAX_TAGS} short non-empty strings")
        path = safe_relative_path(item.get("file"))
        if not path.startswith("prompts/") or not path.endswith(".md"):
            raise PackError(f"{label}: file must be a .md file under prompts/")
        if path in files:
            raise PackError(f"{label}: file {path!r} is used twice")
        files.add(path)
        if not isinstance(item.get("sha256"), str) or not SHA256.match(item["sha256"]):
            raise PackError(f"{label}: sha256 must be 64 lowercase hex characters")
    return manifest


def _check_prompt_bytes(data: bytes, label: str) -> None:
    if not data.strip():
        raise PackError(f"{label}: file is empty")
    if len(data) > MAX_FILE_BYTES:
        raise PackError(f"{label}: file is larger than {MAX_FILE_BYTES} bytes")
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        raise PackError(f"{label}: file is not UTF-8")


def load_pack(directory: Path) -> Dict[str, Any]:
    """Validate a pack directory and return its manifest. Every file must be accounted for."""
    directory = Path(directory)
    manifest_path = directory / "pack.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise PackError(f"{directory.name}: pack.json is missing")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PackError(f"{directory.name}/pack.json: not valid JSON ({error})")
    validate_manifest(manifest, f"{directory.name}/pack.json")
    if manifest["id"] != directory.name:
        raise PackError(f"{directory.name}: directory name must equal the pack id {manifest['id']!r}")
    listed = set()
    total = 0
    for item in manifest["items"]:
        path = directory / item["file"]
        if path.is_symlink() or not path.is_file():
            raise PackError(f"{directory.name}: {item['file']} is missing or not a regular file")
        data = path.read_bytes()
        _check_prompt_bytes(data, f"{directory.name}/{item['file']}")
        if sha256_hex(data) != item["sha256"]:
            raise PackError(f"{directory.name}/{item['file']}: sha256 does not match pack.json")
        listed.add(item["file"])
        total += len(data)
    if total > MAX_PACK_BYTES:
        raise PackError(f"{directory.name}: files add up to more than {MAX_PACK_BYTES} bytes")
    for found in sorted(directory.rglob("*")):
        relative = found.relative_to(directory).as_posix()
        if found.is_symlink():
            raise PackError(f"{directory.name}: symlinks are not allowed ({relative})")
        if found.is_dir() or relative == "pack.json":
            continue
        if relative not in listed:
            raise PackError(f"{directory.name}: {relative} is not listed in pack.json")
    return manifest


def build_zip(directory: Path) -> bytes:
    """A deterministic archive: same pack, same bytes, so hashes are reproducible."""
    directory = Path(directory)
    manifest = load_pack(directory)
    names = ["pack.json"] + sorted(item["file"] for item in manifest["items"])
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in names:
            info = zipfile.ZipInfo(name, date_time=ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o644 << 16
            archive.writestr(info, (directory / name).read_bytes())
    return buffer.getvalue()


def check_zip(data: bytes, expected: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """What the app does on install: open the archive, distrust every name, re-check every rule."""
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as error:
        raise PackError(f"archive is not a zip file ({error})")
    with archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if len(set(names)) != len(names):
            raise PackError("archive has duplicate entries")
        for info in infos:
            safe_relative_path(info.filename)
            if info.is_dir() or (info.external_attr >> 28) == 0xA:
                raise PackError(f"archive entry {info.filename!r} is a directory or a link")
            if info.file_size > MAX_FILE_BYTES:
                raise PackError(f"archive entry {info.filename!r} is too large")
        if "pack.json" not in names:
            raise PackError("archive has no pack.json")
        try:
            manifest = json.loads(archive.read("pack.json").decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise PackError(f"pack.json is not valid JSON ({error})")
        validate_manifest(manifest, "pack.json")
        listed = {item["file"] for item in manifest["items"]}
        if set(names) != listed | {"pack.json"}:
            raise PackError("archive entries do not match pack.json")
        for item in manifest["items"]:
            data_item = archive.read(item["file"])
            _check_prompt_bytes(data_item, item["file"])
            if sha256_hex(data_item) != item["sha256"]:
                raise PackError(f"{item['file']}: sha256 does not match pack.json")
    if expected is not None:
        for key in ("id", "version"):
            if manifest[key] != expected.get(key):
                raise PackError(f"archive {key} {manifest[key]!r} differs from the index ({expected.get(key)!r})")
    return manifest


def build_index(packs_dir: Path, out_dir: Path, base_url: str, generated_at: str) -> Dict[str, Any]:
    """Write every pack archive and index.json into out_dir; return the index."""
    packs_dir, out_dir = Path(packs_dir), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    entries: List[Dict[str, Any]] = []
    for directory in sorted(p for p in packs_dir.iterdir() if p.is_dir()):
        manifest = load_pack(directory)
        archive = build_zip(directory)
        if len(archive) > MAX_ARCHIVE_BYTES:
            raise PackError(f"{manifest['id']}: archive is larger than {MAX_ARCHIVE_BYTES} bytes")
        filename = f"{manifest['id']}-{manifest['version']}.zip"
        (out_dir / filename).write_bytes(archive)
        entries.append(
            {
                "id": manifest["id"],
                "version": manifest["version"],
                "min_app_version": manifest["min_app_version"],
                "kind": manifest["kind"],
                "name": manifest["name"],
                "description": manifest["description"],
                "tools": manifest["tools"],
                "item_count": len(manifest["items"]),
                "url": f"{base_url.rstrip('/')}/{filename}",
                "sha256": sha256_hex(archive),
                "size": len(archive),
            }
        )
    ids = [entry["id"] for entry in entries]
    if len(set(ids)) != len(ids):
        raise PackError("two packs share an id")
    index = {"schema": SCHEMA, "generated_at": generated_at, "packs": entries}
    (out_dir / "index.json").write_bytes(canonical_json(index))
    return index


def verify_release(out_dir: Path) -> Dict[str, Any]:
    """Check a built directory the way a downloading app would, minus the signature."""
    out_dir = Path(out_dir)
    try:
        index = json.loads((out_dir / "index.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PackError(f"index.json is unreadable ({error})")
    if index.get("schema") != SCHEMA or not isinstance(index.get("packs"), list):
        raise PackError("index.json has the wrong shape")
    for entry in index["packs"]:
        filename = entry["url"].rsplit("/", 1)[-1]
        safe_relative_path(filename)
        path = out_dir / filename
        if not path.is_file():
            raise PackError(f"{filename} is listed in the index but missing")
        data = path.read_bytes()
        if len(data) != entry["size"] or sha256_hex(data) != entry["sha256"]:
            raise PackError(f"{filename} does not match the size and sha256 in the index")
        check_zip(data, entry)
    return index
