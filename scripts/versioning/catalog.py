from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "versions" / "catalog.yml"
UPSTREAM_MANIFEST_PATH = ROOT / "versions" / "upstream-versions.yml"
HEX_COMMIT = re.compile(r"^[0-9a-f]{40}$")
VERSION = re.compile(r"^[0-9]+(?:\.[0-9]+){1,2}$")
RELEASE_VERSION = re.compile(r"^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
FAMILIES = {"legacy", "modern"}
STATUSES = {"planned", "branch-ready", "build-checked", "runtime-checked", "released"}
REQUIRED_ROOT_FIELDS = {"schema_version", "versions"}
REQUIRED_VERSION_FIELDS = {"minecraft", "branch", "upstream", "build", "status", "release"}
REQUIRED_UPSTREAM_FIELDS = {"repository", "ref", "commit"}
REQUIRED_BUILD_FIELDS = {
    "family", "jdk", "runtime_java", "patch_roots", "apply_command",
    "check_command", "jar_command", "jar_path",
}
REQUIRED_RELEASE_FIELDS = {"tag_pattern", "asset_name"}


class CatalogError(ValueError):
    pass


def _require_fields(value: dict[str, Any], required: set[str], context: str) -> None:
    missing = required - value.keys()
    extra = value.keys() - required
    if missing:
        raise CatalogError(f"{context}: missing fields: {', '.join(sorted(missing))}")
    if extra:
        raise CatalogError(f"{context}: unknown fields: {', '.join(sorted(extra))}")


def validate_catalog(data: Any) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        raise CatalogError("catalog: expected a mapping")
    _require_fields(data, REQUIRED_ROOT_FIELDS, "catalog")
    if data["schema_version"] != 1:
        raise CatalogError("catalog: schema_version must be 1")
    versions = data["versions"]
    if not isinstance(versions, list) or not versions:
        raise CatalogError("catalog: versions must be a non-empty list")

    seen_versions: set[str] = set()
    seen_branches: set[str] = set()
    main_entries = 0
    for entry in versions:
        if not isinstance(entry, dict):
            raise CatalogError("version entry: expected a mapping")
        version = str(entry.get("minecraft", "<unknown>"))
        context = f"version {version}"
        _require_fields(entry, REQUIRED_VERSION_FIELDS, context)
        minecraft = entry["minecraft"]
        if not isinstance(minecraft, str) or not VERSION.fullmatch(minecraft):
            raise CatalogError(f"{context}: invalid Minecraft version")
        if minecraft in seen_versions:
            raise CatalogError(f"{context}: duplicate Minecraft version")
        seen_versions.add(minecraft)

        branch = entry["branch"]
        if not isinstance(branch, str) or branch not in {"main", f"version/{minecraft}"}:
            raise CatalogError(f"{context}: branch must be main or version/{minecraft}")
        if branch in seen_branches:
            raise CatalogError(f"{context}: duplicate branch {branch}")
        seen_branches.add(branch)
        main_entries += branch == "main"

        upstream = entry["upstream"]
        if not isinstance(upstream, dict):
            raise CatalogError(f"{context}: upstream must be a mapping")
        _require_fields(upstream, REQUIRED_UPSTREAM_FIELDS, context + " upstream")
        if not isinstance(upstream["repository"], str) or not REPOSITORY.fullmatch(upstream["repository"]):
            raise CatalogError(f"{context}: invalid upstream repository")
        if not isinstance(upstream["ref"], str) or not upstream["ref"].strip():
            raise CatalogError(f"{context}: upstream ref is required")
        if not isinstance(upstream["commit"], str) or not HEX_COMMIT.fullmatch(upstream["commit"]):
            raise CatalogError(f"{context}: upstream commit must be a full lowercase SHA-1")

        build = entry["build"]
        if not isinstance(build, dict):
            raise CatalogError(f"{context}: build must be a mapping")
        _require_fields(build, REQUIRED_BUILD_FIELDS, context + " build")
        if not isinstance(build["family"], str) or build["family"] not in FAMILIES:
            raise CatalogError(f"{context}: unknown build family {build['family']!r}")
        supported_javas = {8, 11, 16, 17, 21, 25}
        if (
            not isinstance(build["jdk"], int)
            or not isinstance(build["runtime_java"], int)
            or build["jdk"] not in supported_javas
            or build["runtime_java"] not in supported_javas
        ):
            raise CatalogError(f"{context}: unsupported build JDK or runtime Java")
        if not isinstance(build["patch_roots"], list) or not build["patch_roots"]:
            raise CatalogError(f"{context}: patch_roots must be a non-empty list")
        for key in ("apply_command", "check_command", "jar_command", "jar_path"):
            if not isinstance(build[key], str) or not build[key].strip():
                raise CatalogError(f"{context}: {key} is required")
        if build["family"] == "legacy" and build["jdk"] < 17:
            raise CatalogError(f"{context}: BeefMC 1.8.8 requires build JDK 17 or newer")
        if not isinstance(entry["status"], str) or entry["status"] not in STATUSES:
            raise CatalogError(f"{context}: invalid status {entry['status']!r}")

        release = entry["release"]
        if not isinstance(release, dict):
            raise CatalogError(f"{context}: release must be a mapping")
        _require_fields(release, REQUIRED_RELEASE_FIELDS, context + " release")
        expected_tag = "v{release}"
        expected_asset = f"BeefMC-{minecraft}-v{{release}}.jar"
        if release["tag_pattern"] != expected_tag or release["asset_name"] != expected_asset:
            raise CatalogError(f"{context}: inconsistent release metadata")

    if main_entries != 1:
        raise CatalogError("catalog: exactly one version must map to main")
    return versions


def load_catalog(path: Path = CATALOG_PATH) -> list[dict[str, Any]]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise CatalogError(f"catalog: cannot read {path}: {error}") from error
    entries = validate_catalog(data)
    manifest = load_upstream_manifest()
    if len(entries) != len(manifest):
        raise CatalogError(f"catalog has {len(entries)} versions but upstream manifest has {len(manifest)}")
    keys = ("minecraft", "branch")
    upstream_keys = ("repository", "ref", "commit")
    for entry, upstream_entry in zip(entries, manifest, strict=True):
        if any(entry[key] != upstream_entry[key] for key in keys) or any(
            entry["upstream"][key] != upstream_entry["upstream"][key] for key in upstream_keys
        ):
            raise CatalogError(f"version {entry['minecraft']}: catalog does not match upstream manifest")
    return entries


def load_upstream_manifest(path: Path = UPSTREAM_MANIFEST_PATH) -> list[dict[str, Any]]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise CatalogError(f"upstream manifest: cannot read {path}: {error}") from error
    if not isinstance(data, dict) or set(data) != {"schema_version", "versions"} or data["schema_version"] != 1:
        raise CatalogError("upstream manifest: invalid root or schema version")
    versions = data["versions"]
    if not isinstance(versions, list) or not versions:
        raise CatalogError("upstream manifest: versions must be a non-empty list")
    seen: set[str] = set()
    main_entries = 0
    for entry in versions:
        if not isinstance(entry, dict) or set(entry) != {"minecraft", "branch", "upstream"}:
            raise CatalogError("upstream manifest: each version needs minecraft, branch, and upstream")
        minecraft = entry["minecraft"]
        if not isinstance(minecraft, str) or not VERSION.fullmatch(minecraft) or minecraft in seen:
            raise CatalogError(f"upstream manifest: invalid or duplicate version {minecraft!r}")
        seen.add(minecraft)
        expected_branch = "main" if minecraft == "26.3" else f"version/{minecraft}"
        if entry["branch"] != expected_branch:
            raise CatalogError(f"upstream manifest: version {minecraft} must use branch {expected_branch}")
        main_entries += entry["branch"] == "main"
        upstream = entry["upstream"]
        if (
            not isinstance(upstream, dict)
            or set(upstream) != {"repository", "ref", "commit"}
            or not isinstance(upstream["repository"], str)
            or not REPOSITORY.fullmatch(upstream["repository"])
            or not isinstance(upstream["ref"], str)
            or not upstream["ref"].strip()
            or not isinstance(upstream["commit"], str)
            or not HEX_COMMIT.fullmatch(upstream["commit"])
        ):
            raise CatalogError(f"upstream manifest: invalid upstream pin for {minecraft}")
    if main_entries != 1:
        raise CatalogError("upstream manifest: exactly current version 26.3 must use main")
    return versions


def entry_for_branch(branch: str, entries: list[dict[str, Any]]) -> dict[str, Any]:
    matches = [entry for entry in entries if entry["branch"] == branch]
    if len(matches) != 1:
        raise CatalogError(f"branch {branch!r}: expected one catalog entry, found {len(matches)}")
    return matches[0]


def release_version_for_tag(tag: str) -> str:
    match = RELEASE_VERSION.fullmatch(tag)
    if match is None:
        raise CatalogError(f"tag {tag!r}: expected vMAJOR.MINOR.PATCH")
    return ".".join(match.groups())


def matrix_for_selector(selector: str, entries: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    if selector == "all":
        selected = entries
    else:
        branch = selector if selector == "main" or selector.startswith("version/") else (
            "main" if selector == "26.3" else f"version/{selector}"
        )
        selected = [entry_for_branch(branch, entries)]
    return {
        "include": [
            {
                "minecraft": entry["minecraft"],
                "branch": entry["branch"],
                "build_family": entry["build"]["family"],
                "build_jdk": entry["build"]["jdk"],
            }
            for entry in selected
        ]
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and resolve BeefMC version metadata")
    parser.add_argument("command", choices=("validate", "resolve-branch", "resolve-release", "matrix"))
    parser.add_argument("value", nargs="?", help="branch, version, release tag, or all")
    args = parser.parse_args()
    try:
        entries = load_catalog()
        if args.command == "validate":
            print(f"Validated {len(entries)} version entries")
            return 0
        if args.command == "matrix":
            print("matrix=" + json.dumps(matrix_for_selector(args.value or "all", entries), separators=(",", ":")))
            return 0
        if args.value is None:
            raise CatalogError(f"{args.command} requires a value")
        if args.command == "resolve-branch":
            entry = entry_for_branch(args.value, entries)
            print(f"minecraft={entry['minecraft']}")
            print(f"branch={entry['branch']}")
            print(f"source_ref={entry['branch']}")
            print(f"build_family={entry['build']['family']}")
            print(f"build_jdk={entry['build']['jdk']}")
            print(f"runtime_java={entry['build']['runtime_java']}")
            print(f"apply_command={entry['build']['apply_command']}")
            print(f"check_command={entry['build']['check_command']}")
            print(f"jar_command={entry['build']['jar_command']}")
            print(f"jar_path={entry['build']['jar_path']}")
        else:
            release_version = release_version_for_tag(args.value)
            print(f"release_version={release_version}")
            print("matrix=" + json.dumps(matrix_for_selector("all", entries)["include"], separators=(",", ":")))
        return 0
    except CatalogError as error:
        print(error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
