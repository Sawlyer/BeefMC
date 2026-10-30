from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from catalog import CatalogError, load_catalog


ROOT = Path(__file__).resolve().parents[2]
REPOSITORY = "Sawlyer/BeefMC"


def git(root: Path, *arguments: str, env: dict[str, str] | None = None, input_text: str | None = None) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=root,
        env=env,
        input=input_text,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise CatalogError(result.stderr.strip() or f"git {' '.join(arguments)} failed")
    return result.stdout.strip()


def tree_records(root: Path, tree: str) -> list[bytes]:
    result = subprocess.run(
        ["git", "ls-tree", "-z", tree],
        cwd=root,
        capture_output=True,
        check=True,
    )
    return [record for record in result.stdout.split(b"\0") if record]


def make_tree(root: Path, records: list[bytes]) -> str:
    result = subprocess.run(
        ["git", "mktree", "--missing", "-z"],
        cwd=root,
        input=b"\0".join(records) + (b"\0" if records else b""),
        capture_output=True,
        check=True,
    )
    return result.stdout.decode("ascii").strip()


def replace_tree_child(root: Path, parent_tree: str, child_name: str, child_tree: str) -> str:
    wanted = child_name.encode("utf-8")
    replacement = f"040000 tree {child_tree}".encode("ascii") + b"\t" + wanted
    records = tree_records(root, parent_tree)
    replaced = False
    updated: list[bytes] = []
    for record in records:
        _, name = record.split(b"\t", 1)
        if name == wanted:
            updated.append(replacement)
            replaced = True
        else:
            updated.append(record)
    if not replaced:
        updated.append(replacement)
    return make_tree(root, updated)


def branch_workflow(version: str, branch: str) -> str:
    return f"""name: BeefMC version CI

on:
  push:
    branches:
      - {branch}
  pull_request:
    branches:
      - {branch}

permissions:
  contents: read

jobs:
  build:
    uses: {REPOSITORY}/.github/workflows/version-ci.yml@main
    with:
      source_ref: ${{{{ github.event.pull_request.head.ref || github.ref_name }}}}
      version_branch: {branch}
      tooling_ref: main
"""


def create_branch_workflow_commit(
    root: Path,
    version: str,
    branch: str,
    base_commit: str,
) -> str | None:
    ref = f"refs/heads/{branch}"
    existing = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", ref],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if existing.returncode == 0:
        return None
    git(root, "cat-file", "-e", f"{base_commit}^{{commit}}")
    base_tree = git(root, "show", "-s", "--format=%T", base_commit)
    github_tree = None
    for record in tree_records(root, base_tree):
        header, name = record.split(b"\t", 1)
        if name == b".github" and header.startswith(b"040000 tree "):
            github_tree = header.split(b" ", 2)[2].decode("ascii")
            break
    empty_tree = make_tree(root, [])
    workflow_blob = subprocess.run(
        ["git", "hash-object", "-w", "--stdin"],
        cwd=root,
        input=branch_workflow(version, branch).encode("utf-8"),
        capture_output=True,
        check=True,
    ).stdout.decode("ascii").strip()
    workflow_tree = make_tree(
        root,
        [f"100644 blob {workflow_blob}".encode("ascii") + b"\tci.yml"],
    )
    github_tree = replace_tree_child(root, github_tree or empty_tree, "workflows", workflow_tree)
    tree = replace_tree_child(root, base_tree, ".github", github_tree)
    message = f"ci: delegate {version} builds to shared BeefMC workflow\n"
    commit = subprocess.run(
        [
            "git",
            "-c",
            "user.name=BeefMC Branch Setup",
            "-c",
            "user.email=beefmc-automation@users.noreply.github.com",
            "commit-tree",
            tree,
            "-p",
            base_commit,
        ],
        cwd=root,
        input=message,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    git(root, "update-ref", ref, commit)
    return commit


def main() -> int:
    parser = argparse.ArgumentParser(description="Create local version branches with BeefMC CI entry points")
    parser.add_argument("--version", action="append", help="one Minecraft version; omit to create all missing historical branches")
    args = parser.parse_args()
    try:
        entries = load_catalog()
        selected = {value for value in args.version} if args.version else None
        created = 0
        skipped = 0
        for entry in entries:
            version = entry["minecraft"]
            branch = entry["branch"]
            if branch == "main" or (selected is not None and version not in selected):
                continue
            commit = create_branch_workflow_commit(ROOT, version, branch, entry["upstream"]["commit"])
            if commit is None:
                print(f"preserved {branch}: branch already exists")
                skipped += 1
            else:
                print(f"created {branch}: {commit}")
                created += 1
        if selected is not None:
            known = {entry["minecraft"] for entry in entries}
            unknown = selected - known
            if unknown:
                raise CatalogError(f"unknown Minecraft version(s): {', '.join(sorted(unknown))}")
        print(f"created={created} preserved={skipped}")
        return 0
    except (CatalogError, subprocess.CalledProcessError) as error:
        print(error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
