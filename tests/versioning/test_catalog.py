from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "versioning"))

from catalog import CatalogError, entry_for_branch, load_catalog, load_upstream_manifest, matrix_for_selector, release_version_for_tag, validate_catalog
from release import package_asset, select_jar, validate_release


class CatalogValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.valid = {"schema_version": 1, "versions": load_catalog()}

    def mutate(self, callback) -> dict:
        data = copy.deepcopy(self.valid)
        callback(data)
        return data

    def test_repository_catalog_is_valid(self) -> None:
        entries = validate_catalog(self.valid)
        manifest = load_upstream_manifest()
        self.assertEqual(4, len(entries))
        self.assertEqual([item["minecraft"] for item in manifest], [item["minecraft"] for item in entries])

    def test_manifest_pins_every_supported_stable_ref(self) -> None:
        manifest = load_upstream_manifest()
        expected = [
            "1.8.8", "1.21.11", "26.1.2", "26.3",
        ]
        self.assertEqual(expected, [item["minecraft"] for item in manifest])
        self.assertEqual(1, sum(item["branch"] == "main" for item in validate_catalog(self.valid)))

    def test_ci_matrix_resolves_all_versions_or_one_selected_version(self) -> None:
        entries = validate_catalog(self.valid)
        all_targets = matrix_for_selector("all", entries)["include"]
        self.assertEqual(4, len(all_targets))
        selected = matrix_for_selector("1.21.11", entries)["include"]
        self.assertEqual([{"minecraft": "1.21.11", "branch": "version/1.21.11", "build_family": "modern", "build_jdk": 21}], selected)
        selected_2612 = matrix_for_selector("26.1.2", entries)["include"]
        self.assertEqual(
            [{"minecraft": "26.1.2", "branch": "version/26.1.2", "build_family": "modern", "build_jdk": 25}],
            selected_2612,
        )

    def test_resolves_legacy_and_new_version_branch_names(self) -> None:
        versions = validate_catalog(self.valid)
        self.assertEqual("1.8.8", entry_for_branch("version/1.8.8", versions)["minecraft"])
        self.assertEqual("26.3", entry_for_branch("main", versions)["minecraft"])

    def test_legacy_jar_command_and_path_use_beefmc_names(self) -> None:
        entry = next(item for item in validate_catalog(self.valid) if item["minecraft"] == "1.8.8")
        self.assertEqual("./beefmc jar", entry["build"]["jar_command"])
        self.assertEqual("beefmc-1.8.8.jar", entry["build"]["jar_path"])

    def test_resolves_common_release_tag(self) -> None:
        self.assertEqual("0.0.0", release_version_for_tag("v0.0.0"))
        self.assertEqual("1.2.3", release_version_for_tag("v1.2.3"))

    def test_duplicate_minecraft_version_is_rejected(self) -> None:
        data = self.mutate(lambda value: value["versions"].append(copy.deepcopy(value["versions"][0])))
        with self.assertRaisesRegex(CatalogError, "duplicate Minecraft version"):
            validate_catalog(data)

    def test_invalid_branch_is_rejected(self) -> None:
        data = self.mutate(lambda value: value["versions"][0].update(branch="version/1.8"))
        with self.assertRaisesRegex(CatalogError, "version/1.8.8"):
            validate_catalog(data)

    def test_unknown_build_family_is_rejected(self) -> None:
        data = self.mutate(lambda value: value["versions"][0]["build"].update(family="unknown"))
        with self.assertRaisesRegex(CatalogError, "unknown build family"):
            validate_catalog(data)

    def test_release_metadata_must_match_version(self) -> None:
        data = self.mutate(lambda value: value["versions"][0]["release"].update(asset_name="Paper-{release}.jar"))
        with self.assertRaisesRegex(CatalogError, "inconsistent release metadata"):
            validate_catalog(data)

    def test_unknown_or_malformed_release_tag_is_rejected(self) -> None:
        for tag in ("beefmc-1.8.8-r1", "v01.0.0", "v1.0", "v1.0.0-rc1"):
            with self.subTest(tag=tag), self.assertRaises(CatalogError):
                release_version_for_tag(tag)

    def test_release_is_blocked_until_runtime_checks_pass(self) -> None:
        data = self.mutate(lambda value: value["versions"][0].update(status="build-checked"))
        with tempfile.TemporaryDirectory() as temporary:
            catalog_path = Path(temporary) / "catalog.yml"
            catalog_path.write_text(yaml.safe_dump(data), encoding="utf-8")
            with self.assertRaisesRegex(CatalogError, "release blocked while status is 'build-checked'"):
                validate_release("v1.0.0", "0" * 40, source_root=ROOT, catalog_path=catalog_path)

    def test_exactly_one_version_uses_main(self) -> None:
        data = self.mutate(lambda value: value["versions"][1].update(branch="main"))
        with self.assertRaisesRegex(CatalogError, "duplicate branch"):
            validate_catalog(data)

    def test_modern_release_selects_one_bundler_not_server_intermediate(self) -> None:
        entry = copy.deepcopy(next(item for item in validate_catalog(self.valid) if item["minecraft"] == "1.21.11"))
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            root = Path(temporary)
            libs = root / "leaf-server" / "build" / "libs"
            libs.mkdir(parents=True)
            (libs / "paper-server-1.21.11-R0.1-SNAPSHOT.jar").write_bytes(b"intermediate")
            final_jar = libs / "beefmc-paperclip-1.21.11.jar"
            final_jar.write_bytes(b"bundler")
            self.assertEqual(final_jar, select_jar(entry, root))

    def test_modern_1_21_11_jar_command_uses_mojmap_paperclip(self) -> None:
        entry = next(item for item in validate_catalog(self.valid) if item["minecraft"] == "1.21.11")
        self.assertEqual("./gradlew :beefmc-server:createMojmapPaperclipJar", entry["build"]["jar_command"])

    def test_modern_versions_use_beefmc_gradle_paths_and_jar_names(self) -> None:
        for entry in validate_catalog(self.valid):
            if entry["minecraft"] == "1.8.8":
                continue
            with self.subTest(version=entry["minecraft"]):
                build = entry["build"]
                self.assertIn(":beefmc-server:", build["jar_command"])
                self.assertEqual("leaf-server/build/libs/beefmc-paperclip-*.jar", build["jar_path"])

    def test_modern_paperclip_task_writes_to_beefmc_filename(self) -> None:
        patch = ROOT / "leaf-server" / "build.gradle.kts.patch"
        if not patch.exists():
            self.skipTest("this version branch has no modern Paperclip task")
        content = patch.read_text(encoding="utf-8")
        self.assertIn("CreatePaperclipJar>(\"create", content)
        self.assertIn('outputZip.set(layout.buildDirectory.file("libs/$jarName"))', content)
        suite_patch = ROOT / "leaf-server" / "paper-patches" / "features" / "0008-Leaf-JUnit-test-suite.patch"
        suite_content = suite_patch.read_text(encoding="utf-8")
        self.assertIn('@SuiteDisplayName("Test suite for tests used by BeefMC")', suite_content)
        self.assertNotIn('@SuiteDisplayName("Test suite for tests used by Leaf")', suite_content)

    def test_release_jar_selection_fails_on_ambiguous_final_jars(self) -> None:
        entry = copy.deepcopy(next(item for item in validate_catalog(self.valid) if item["minecraft"] == "1.21.11"))
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            root = Path(temporary)
            libs = root / "leaf-server" / "build" / "libs"
            libs.mkdir(parents=True)
            (libs / "beefmc-paperclip-a.jar").write_bytes(b"one")
            (libs / "beefmc-paperclip-b.jar").write_bytes(b"two")
            with self.assertRaisesRegex(CatalogError, "expected exactly one final jar"):
                select_jar(entry, root)

    def test_release_asset_name_and_sha256_are_stable(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            root = Path(temporary)
            libs = root / "leaf-server" / "build" / "libs"
            libs.mkdir(parents=True)
            (libs / "beefmc-paperclip-26.3.build.1-alpha.jar").write_bytes(b"release candidate")
            asset, checksum = package_asset("v0.0.0", "26.3", root)
            self.assertEqual("BeefMC-26.3-v0.0.0.jar", asset.name)
            self.assertEqual("BeefMC-26.3-v0.0.0.jar.sha256", checksum.name)
            self.assertIn(asset.name, checksum.read_text(encoding="ascii"))


if __name__ == "__main__":
    unittest.main()
