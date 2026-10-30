from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

from catalog import CATALOG_PATH, CatalogError, entry_for_branch, load_catalog, release_version_for_tag


ROOT = CATALOG_PATH.parents[1]


def validate_release(
    tag: str,
    commit: str,
    prerelease: bool = False,
    source_root: Path = ROOT,
    catalog_path: Path = CATALOG_PATH,
) -> tuple[list[dict], str]:
    release_version = release_version_for_tag(tag)
    entries = load_catalog(catalog_path)
    initial_release = release_version == "0.0.0"
    if initial_release and not prerelease:
        raise CatalogError("v0.0.0 must be published as a pre-release")
    accepted_statuses = (
        {"branch-ready", "build-checked", "runtime-checked", "released"}
        if initial_release
        else {"runtime-checked", "released"}
    )
    for entry in entries:
        if entry["status"] not in accepted_statuses:
            raise CatalogError(f"version {entry['minecraft']}: release blocked while status is {entry['status']!r}")
    try:
        subprocess.run(["git", "rev-parse", "--verify", "origin/main"], cwd=source_root, check=True, capture_output=True, text=True)
        subprocess.run(["git", "merge-base", "--is-ancestor", commit, "origin/main"], cwd=source_root, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as error:
        raise CatalogError(f"tag {tag!r}: tagged commit is not contained in origin/main") from error
    return entries, release_version


def select_jar(entry: dict, root: Path = ROOT) -> Path:
    pattern = entry["build"]["jar_path"]
    target = root / pattern
    if target.is_file():
        matches = [target]
    elif "*" in pattern or "?" in pattern or "[" in pattern:
        matches = list(root.glob(pattern))
    elif target.is_dir():
        matches = [path for path in target.glob("*.jar") if not path.name.startswith("paper-server-")]
    else:
        matches = []
    matches = [
        path for path in matches
        if path.is_file()
        and not path.name.startswith("paper-server-")
        and not path.name.endswith(("-sources.jar", "-javadoc.jar", "-dev.jar", "-original.jar"))
    ]
    if len(matches) != 1:
        raise CatalogError(f"version {entry['minecraft']}: expected exactly one final jar at {pattern}, found {len(matches)}")
    return matches[0]


def package_asset(
    tag: str,
    minecraft: str,
    source_root: Path = ROOT,
    catalog_path: Path = CATALOG_PATH,
) -> tuple[Path, Path]:
    release_version = release_version_for_tag(tag)
    branch = "main" if minecraft == "26.3" else f"version/{minecraft}"
    entry = entry_for_branch(branch, load_catalog(catalog_path))
    jar = select_jar(entry, source_root)
    asset_dir = source_root / "dist"
    asset_dir.mkdir(exist_ok=True)
    asset = asset_dir / entry["release"]["asset_name"].replace("{release}", release_version)
    shutil.copy2(jar, asset)
    digest = hashlib.sha256(asset.read_bytes()).hexdigest()
    checksum = asset.with_suffix(asset.suffix + ".sha256")
    checksum.write_text(f"{digest}  {asset.name}\n", encoding="ascii")
    return asset, checksum


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a multi-version BeefMC release and package one version jar")
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate")
    validate.add_argument("tag")
    validate.add_argument("commit")
    validate.add_argument("--prerelease", action="store_true")
    validate.add_argument("--source-root", type=Path, default=ROOT)
    validate.add_argument("--catalog", type=Path, default=CATALOG_PATH)
    package = subparsers.add_parser("package")
    package.add_argument("tag")
    package.add_argument("minecraft")
    package.add_argument("--source-root", type=Path, default=ROOT)
    package.add_argument("--catalog", type=Path, default=CATALOG_PATH)
    args = parser.parse_args()
    try:
        if args.command == "validate":
            entries, release_version = validate_release(
                args.tag, args.commit, args.prerelease, args.source_root, args.catalog
            )
            print(f"release_version={release_version}")
            print(f"matrix_count={len(entries)}")
        else:
            asset, checksum = package_asset(args.tag, args.minecraft, args.source_root, args.catalog)
            print(f"asset={asset.relative_to(args.source_root).as_posix()}")
            print(f"checksum={checksum.relative_to(args.source_root).as_posix()}")
        return 0
    except CatalogError as error:
        print(error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
