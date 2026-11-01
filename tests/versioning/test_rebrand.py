from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "versioning"))

from rebrand import apply_rebrand


class RebrandTests(unittest.TestCase):
    def test_rebrands_runtime_and_manifest_but_keeps_paper_compatibility_id(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            source = Path(temporary)
            server = source / "src/main/java/org/bukkit/craftbukkit/CraftServer.java"
            server.parent.mkdir(parents=True)
            server.write_text('private final String serverName = "Paper";\n', encoding="utf-8")

            minecraft = source / "src/main/java/net/minecraft/server/MinecraftServer.java"
            minecraft.parent.mkdir(parents=True)
            minecraft.write_text(
                'public String getServerModName() { return "Paper"; }\n', encoding="utf-8"
            )

            watchdog = source / "src/main/java/org/spigotmc/WatchdogThread.java"
            watchdog.parent.mkdir(parents=True)
            watchdog.write_text(
                '"Paper version:"; "Paper bug"; "https://github.com/PaperMC/Paper/issues";\n',
                encoding="utf-8",
            )

            build = source / "paper-server/build.gradle.kts"
            build.parent.mkdir(parents=True)
            build.write_text(
                '"Implementation-Title" to "Paper"\n'
                '"Specification-Title" to "Paper"\n'
                '"Brand-Id" to "papermc:paper"\n'
                '"Brand-Name" to "Paper"\n',
                encoding="utf-8",
            )

            changes = apply_rebrand(source, "26.3", "modern")

            self.assertEqual(4, len(changes))
            self.assertIn('serverName = "BeefMC"', server.read_text(encoding="utf-8"))
            self.assertIn('return "BeefMC"', minecraft.read_text(encoding="utf-8"))
            self.assertIn("BeefMC version:", watchdog.read_text(encoding="utf-8"))
            metadata = build.read_text(encoding="utf-8")
            self.assertIn('"Brand-Name" to "BeefMC"', metadata)
            self.assertIn('"Brand-Id" to "papermc:paper"', metadata)

    def test_rebrand_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            source = Path(temporary)
            server = source / "src/main/java/org/bukkit/craftbukkit/CraftServer.java"
            server.parent.mkdir(parents=True)
            server.write_text('private final String serverName = "BeefMC";\n', encoding="utf-8")
            self.assertEqual([], apply_rebrand(source, "1.8.8", "legacy"))

    def test_rebrands_legacy_gradle_project_ids_and_packaging_output(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            source = Path(temporary)
            settings = source / "settings.gradle.kts"
            settings.write_text(
                'rootProject.name = "beefmc"\n'
                'setupSubproject("pandaspigot-server", "PandaSpigot-Server")\n'
                'setupSubproject("pandaspigot-api", "PandaSpigot-API")\n',
                encoding="utf-8",
            )
            packaging = source / "paperclip.sh"
            packaging.write_text(
                'echo "Failed to build Paperclip jar."\n'
                'cp paperclip/build/libs/paperclip-1.8.8-R0.1-SNAPSHOT.jar paperclip.jar\n'
                'echo "Copied final jar to paperclip.jar"\n',
                encoding="utf-8",
            )
            server_build = source / "BeefMC-Server/build.gradle.kts"
            server_build.parent.mkdir(parents=True)
            server_build.write_text(
                'dependencies { implementation(project(":pandaspigot-api")) }\n',
                encoding="utf-8",
            )
            paperclip_build_logic = source / "build-logic/src/main/kotlin/paperclip.gradle.kts"
            paperclip_build_logic.parent.mkdir(parents=True)
            paperclip_build_logic.write_text(
                'dependsOn("shadowJar", ":pandaspigot-server:remap")\n'
                'val server = project(":pandaspigot-server")\n',
                encoding="utf-8",
            )

            apply_rebrand(source, "1.8.8", "legacy")

            settings_result = settings.read_text(encoding="utf-8")
            self.assertIn('setupSubproject("beefmc-server", "BeefMC-Server")', settings_result)
            self.assertIn('setupSubproject("beefmc-api", "BeefMC-API")', settings_result)
            packaging_result = packaging.read_text(encoding="utf-8")
            self.assertIn("beefmc-1.8.8.jar", packaging_result)
            self.assertNotIn("Failed to build Paperclip jar", packaging_result)
            self.assertIn('project(":beefmc-api")', server_build.read_text(encoding="utf-8"))
            build_logic_result = paperclip_build_logic.read_text(encoding="utf-8")
            self.assertNotIn("pandaspigot", build_logic_result)
            self.assertIn(":beefmc-server:remap", build_logic_result)
            self.assertIn('project(":beefmc-server")', build_logic_result)

    def test_rebrands_modern_gradle_settings_messages_and_task_paths(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            source = Path(temporary)
            settings = source / "settings.gradle.kts"
            settings.write_text(
                '// Leaf start - project setup\n'
                'val errorText = "The Leaf project directory is not a properly cloned Git repository. " +\n'
                '    "Clone Leaf from https://www.leafmc.one/download. See " +\n'
                '    "https://github.com/PaperMC/Paper/blob/main/CONTRIBUTING.md for Paper forks."\n'
                '// Leaf end - project setup\n'
                'rootProject.name = "leaf"\n'
                'include("beefmc-api", "beefmc-server")\n',
                encoding="utf-8",
            )

            apply_rebrand(source, "26.3", "modern")

            result = settings.read_text(encoding="utf-8")
            self.assertIn('rootProject.name = "beefmc"', result)
            self.assertIn('include("beefmc-api", "beefmc-server")', result)
            self.assertNotIn("Leaf", result)
            self.assertNotIn("leafmc.one", result)
            self.assertNotIn("Paper forks", result)
            self.assertNotIn("github.com/PaperMC", result)

    def test_rebrands_legacy_watchdog_strings(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            source = Path(temporary)
            watchdog = source / "src/main/java/org/spigotmc/WatchdogThread.java"
            watchdog.parent.mkdir(parents=True)
            watchdog.write_text(
                '"PaperSpigot Watchdog Thread"; '
                '"Please report this to PaperSpigot directly!"; '
                '"PaperSpigot version:"; '
                '"Look for plugins here before reporting to PaperSpigot!";\n',
                encoding="utf-8",
            )

            apply_rebrand(source, "1.8.8", "legacy")

            result = watchdog.read_text(encoding="utf-8")
            self.assertIn("BeefMC Watchdog Thread", result)
            self.assertIn("Please report this to BeefMC at https://github.com/Sawlyer/BeefMC/issues!", result)
            self.assertIn("BeefMC version:", result)
            self.assertIn("reporting to BeefMC!", result)

    def test_legacy_rebrand_ignores_modern_only_source_files(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            source = Path(temporary)
            server = source / "src/main/java/org/bukkit/craftbukkit/CraftServer.java"
            server.parent.mkdir(parents=True)
            server.write_text('private final String serverName = "Paper";\n', encoding="utf-8")
            leaf_command = source / "src/main/java/org/dreeam/leaf/command/ReloadCommand.java"
            leaf_command.parent.mkdir(parents=True)
            leaf_command.write_text("class ReloadCommand {}\n", encoding="utf-8")

            apply_rebrand(source, "1.8.8", "legacy")

            self.assertIn('serverName = "BeefMC"', server.read_text(encoding="utf-8"))
            self.assertEqual("class ReloadCommand {}\n", leaf_command.read_text(encoding="utf-8"))

    def test_fails_when_upstream_layout_has_no_known_branding_anchor(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            source = Path(temporary)
            server = source / "src/main/java/org/bukkit/craftbukkit/CraftServer.java"
            server.parent.mkdir(parents=True)
            server.write_text("public final class CraftServer {}\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "no supported branding markers"):
                apply_rebrand(source, "unknown", "modern")


if __name__ == "__main__":
    unittest.main()
