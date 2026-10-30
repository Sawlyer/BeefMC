from __future__ import annotations

import re
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


class WorkflowContractTests(unittest.TestCase):
    def test_public_contributor_text_does_not_expose_upstream_branding(self) -> None:
        legacy_names = re.compile(r"\b(?:PandaSpigot|Leaf|Paper)\b", re.IGNORECASE)
        for relative_path in (
            "AGENTS.md",
            "CONTRIBUTING.md",
            "docs/architecture/version-support.md",
            ".github/pull_request_template.md",
            ".github/ISSUE_TEMPLATE/en_bug_report.yml",
            ".github/ISSUE_TEMPLATE/en_feature_request.yml",
            ".github/ISSUE_TEMPLATE/zh_bug_report.yml",
            ".github/ISSUE_TEMPLATE/zh_feature_request.yml",
        ):
            content = (ROOT / relative_path).read_text(encoding="utf-8")
            self.assertIsNone(legacy_names.search(content), f"legacy branding in {relative_path}")

    def test_ci_has_single_branch_and_full_matrix_paths(self) -> None:
        workflow = yaml.load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
        self.assertIn("schedule", workflow["on"])
        self.assertIn("workflow_dispatch", workflow["on"])
        self.assertIn("build", workflow["jobs"])
        self.assertIn("fromJSON(needs.validate.outputs.matrix)", workflow["jobs"]["build"]["strategy"]["matrix"])
        self.assertIn("github.event.pull_request.head.sha", (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))

    def test_visible_workflow_labels_use_beefmc_names(self) -> None:
        legacy_names = re.compile(r"\b(?:PandaSpigot|Leaf|Paperweight|Paper)\b", re.IGNORECASE)
        for relative_path in (
            ".github/workflows/ci.yml",
            ".github/workflows/version-ci.yml",
            ".github/workflows/release.yml",
        ):
            workflow = yaml.load((ROOT / relative_path).read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
            content = (ROOT / relative_path).read_text(encoding="utf-8")
            self.assertNotIn("./paper ", content, f"stale launcher command in {relative_path}")
            self.assertNotIn("build_family == 'panda'", content, f"legacy family name in {relative_path}")
            self.assertNotIn("build_family == 'leaf'", content, f"modern family name in {relative_path}")
            names = [workflow.get("name", "")]
            for job in workflow.get("jobs", {}).values():
                names.append(job.get("name", ""))
                names.extend(step.get("name", "") for step in job.get("steps", []))
            for name in names:
                self.assertIsNone(legacy_names.search(name), f"legacy name in {relative_path}: {name}")

    def test_reusable_ci_supports_each_build_family_without_packaging_release_jars(self) -> None:
        workflow = yaml.load((ROOT / ".github/workflows/version-ci.yml").read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
        self.assertIn("workflow_call", workflow["on"])
        content = (ROOT / ".github/workflows/version-ci.yml").read_text(encoding="utf-8")
        for family in ("legacy", "modern"):
            self.assertIn(f"build_family == '{family}'", content)
        self.assertIn("github.event.pull_request.head.repo.full_name", content)
        self.assertIn("runtime_validation", workflow["on"]["workflow_call"]["inputs"])
        runtime_jar_steps = [step for step in workflow["jobs"]["build"]["steps"] if "createPaperclipJar" in step.get("run", "")]
        self.assertEqual(len(runtime_jar_steps), 1)
        self.assertIn("inputs.runtime_validation", runtime_jar_steps[0]["if"])
        self.assertNotIn("./paper ", content)

    def test_each_ci_family_applies_beefmc_branding_after_patch_setup(self) -> None:
        content = (ROOT / ".github/workflows/version-ci.yml").read_text(encoding="utf-8")
        self.assertIn("./beefmc setup", content)
        self.assertIn("python tooling/scripts/versioning/rebrand.py apply", content)
        self.assertIn("--family legacy", content)
        self.assertIn("./gradlew applyAllPatches --stacktrace --no-daemon", content)
        self.assertIn("--family modern", content)
        self.assertIn("./gradlew build --stacktrace", content)
        self.assertNotIn("./panda rebuild", content)

    def test_release_builds_every_catalog_version_and_attaches_assets(self) -> None:
        content = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
        self.assertIn("python scripts/versioning/catalog.py matrix all", content)
        self.assertIn("fromJSON(needs.validate.outputs.matrix)", content)
        self.assertIn("python -m pip install --disable-pip-version-check -r tooling/scripts/versioning/requirements.txt", content)
        self.assertIn('if [[ "$MINECRAFT_VERSION" == "1.21.11" ]]', content)
        self.assertIn("./gradlew :beefmc-server:createMojmapPaperclipJar --no-daemon", content)
        self.assertIn("./gradlew :beefmc-server:createPaperclipJar", content)
        self.assertIn("actions/upload-artifact@v7", content)
        self.assertIn("gh release upload", content)
        self.assertIn("github.event.release.prerelease", content)

    def test_rebrand_preserves_compatibility_brand_id(self) -> None:
        if not (ROOT / "leaf-server/paper-patches/features/0002-Rebrand.patch").is_file():
            self.skipTest("modern source patches are not part of this version tree")
        source = (ROOT / "leaf-server/paper-patches/features/0002-Rebrand.patch").read_text(encoding="utf-8")
        api = (ROOT / "leaf-api/paper-patches/features/0002-Rebrand.patch").read_text(encoding="utf-8")
        build = (ROOT / "leaf-server/build.gradle.kts.patch").read_text(encoding="utf-8")
        self.assertIn('BRAND_LEAF_NAME = "Leaf"', source)
        self.assertIn('BRAND_LEAF_ID = Key.key("winds-studio", "leaf")', api)
        self.assertIn('"Brand-Id" to "winds-studio:leaf"', build)

    def test_modern_gradle_task_paths_use_beefmc_project_names(self) -> None:
        settings = (ROOT / "settings.gradle.kts").read_text(encoding="utf-8")
        server_patch = ROOT / "leaf-server/build.gradle.kts.patch"
        if '"beefmc-server" to "leaf-server"' not in settings:
            self.skipTest("modern project settings are not part of this version tree")
        self.assertIn('rootProject.name = "beefmc"', settings)
        self.assertIn('"beefmc-api" to "leaf-api"', settings)
        self.assertIn('"beefmc-server" to "leaf-server"', settings)
        self.assertIn('implementation(project(":beefmc-api"))', server_patch.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
