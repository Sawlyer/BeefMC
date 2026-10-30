from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Change:
    path: Path
    before: str
    after: str


def _replace_server_name(content: str) -> tuple[str, bool]:
    pattern = re.compile(
        r'(?P<prefix>\bserverName\s*=\s*)"(?:Paper|PandaSpigot|PaperSpigot|CraftBukkit)"'
    )
    found = bool(pattern.search(content) or re.search(r'\bserverName\s*=\s*"BeefMC"', content))
    return pattern.sub(r'\g<prefix>"BeefMC"', content), found


def _replace_server_mod_name(content: str) -> tuple[str, bool]:
    pattern = re.compile(
        r'(getServerModName\s*\(\)\s*\{[^}]*?\breturn\s*)"(?:Paper|PandaSpigot|PaperSpigot|vanilla)"',
        re.DOTALL,
    )
    found = bool(pattern.search(content) or re.search(r'getServerModName\s*\(\)[^}]*return\s*"BeefMC"', content, re.DOTALL))
    return pattern.sub(r'\1"BeefMC"', content), found


def _replace_watchdog(content: str) -> tuple[str, bool]:
    replacements = {
        "PaperSpigot Watchdog Thread": "BeefMC Watchdog Thread",
        "PandaSpigot Watchdog Thread": "BeefMC Watchdog Thread",
        "Paper version:": "BeefMC version:",
        "PandaSpigot version:": "BeefMC version:",
        "PaperSpigot version:": "BeefMC version:",
        "Paper bug": "BeefMC bug",
        "PandaSpigot bug": "BeefMC bug",
        "PaperSpigot bug": "BeefMC bug",
        "Please report this to PaperSpigot directly!": "Please report this to BeefMC at https://github.com/Sawlyer/BeefMC/issues!",
        "Please report this in https://github.com/hpfxd/PandaSpigot/issues!": "Please report this in https://github.com/Sawlyer/BeefMC/issues!",
        "reporting to PandaSpigot!": "reporting to BeefMC!",
        "reporting to PaperSpigot!": "reporting to BeefMC!",
        "PaperMC/Paper/issues": "Sawlyer/BeefMC",
        "hpfxd/PandaSpigot/issues": "Sawlyer/BeefMC",
    }
    changed = False
    for before, after in replacements.items():
        if before in content:
            content = content.replace(before, after)
            changed = True
    return content, changed or "BeefMC version:" in content or "BeefMC bug" in content


def _replace_build_info_fallback(content: str, family: str) -> tuple[str, bool]:
    brand_constant = "BRAND_LEAF_NAME" if family == "modern" else "BRAND_PAPER_NAME"
    upstream_brand = "Leaf" if family == "modern" else "Paper"
    pattern = re.compile(rf'({brand_constant}\s*=\s*)"{upstream_brand}"')
    found = bool(pattern.search(content) or re.search(rf'{brand_constant}\s*=\s*"BeefMC"', content))
    return pattern.sub(r'\1"BeefMC"', content), found


def _replace_leaf_config(content: str) -> tuple[str, bool]:
    original = content
    content = re.sub(
        r'((?:I_)?GLOBAL_CONFIG_FILE\s*=\s*)"[^"]+"',
        r'\1"beefmc-global.yml"',
        content,
    )
    content = re.sub(
        r'(?m)^[ \t]*(?:protected )?static final String (?:I_)?(?:DEFAULT_WORLD_CONFIG_FILE|LEVEL_CONFIG_FILE)\s*=\s*"[^"]+";[^\n]*\n',
        "",
        content,
    )
    content = re.sub(r'"config/[^"]*global\.yml"', '"config/beefmc-global.yml"', content)
    content = content.replace(
        'LogManager.getLogger(LeafConfig.class.getSimpleName())',
        'LogManager.getLogger("BeefMC")',
    )
    content = content.replace(
        "Found legacy Leaf config files, move to backup directory: {}",
        "Found legacy configuration files, moving them to backup: {}",
    )
    content = content.replace(
        "New Leaf config located at config/ folder, You need to transfer config to the new one manually and restart the server!",
        "Transfer custom settings from the backup into the BeefMC config, then restart the server.",
    )
    content = content.replace("Leaf's additional light-level check", "BeefMC's additional light-level check")
    content = content.replace("启用 Leaf 额外的光照检查", "启用 BeefMC 额外的光照检查")

    content = re.sub(r'(?m)^[ \t]*String leafConfigV[12] = .*;\n', "", content)
    content = re.sub(r'(?m)^[ \t]*File leafConfigV[12]File = .*;\n', "", content)
    for legacy_file in ("leafConfigV1File", "leafConfigV2File"):
        content = re.sub(
            rf'(?ms)^            if \({legacy_file}\.exists\(\).*?^            }}\n',
            "",
            content,
        )
    return content, content != original or "beefmc-global.yml" in content


def _replace_leaf_global_config(content: str) -> tuple[str, bool]:
    replacements = {
        "Leaf Config": "BeefMC Configuration",
        "Leaf 配置": "BeefMC 配置",
        "Website: https://www.leafmc.one/": "GitHub: https://github.com/Sawlyer/BeefMC",
        "Docs: https://www.leafmc.one/docs/getting-started": "",
        "GitHub Repo: https://github.com/Winds-Studio/Leaf": "",
        "Discord: https://discord.com/invite/gfgAwdSEuM": "",
        "官网: https://www.leafmc.one/zh/": "GitHub: https://github.com/Sawlyer/BeefMC",
        "文档: https://www.leafmc.one/zh/docs/getting-started": "",
        "GitHub 仓库: https://github.com/Winds-Studio/Leaf": "",
        "QQ社区群: 619278377": "",
    }
    changed = False
    for before, after in replacements.items():
        if before in content:
            content = content.replace(before, after)
            changed = True
    return content, changed or "BeefMC Configuration" in content


def _replace_leaf_command(content: str) -> tuple[str, bool]:
    original = content
    content = content.replace('COMMAND_LABEL = "leaf"', 'COMMAND_LABEL = "beefmc"')
    content = content.replace(
        'BASE_PERM = LeafCommands.COMMAND_BASE_PERM + ".leaf"',
        'BASE_PERM = LeafCommands.COMMAND_BASE_PERM + "." + COMMAND_LABEL',
    )
    content = content.replace('this.description = "Leaf related commands";', 'this.description = "BeefMC related commands";')
    content = content.replace('\n        this.setAliases(List.of("leaf"));', "")
    return content, content != original or 'COMMAND_LABEL = "beefmc"' in content


def _replace_leaf_permission_root(content: str) -> tuple[str, bool]:
    original = content
    content = content.replace('LEAF_ROOT = "leaf"', 'LEAF_ROOT = "beefmc"')
    return content, content != original or 'LEAF_ROOT = "beefmc"' in content


def _replace_leaf_command_registration(content: str) -> tuple[str, bool]:
    original = content
    content = content.replace('register(s, "Leaf", command)', 'register(s, "BeefMC", command)')
    return content, content != original or 'register(s, "BeefMC", command)' in content


def _replace_leaf_runtime_strings(content: str) -> tuple[str, bool]:
    replacements = {
        "Leaf Async Pathfinding": "BeefMC Async Pathfinding",
        "Leaf Async Tracker Thread": "BeefMC Async Tracker Thread",
        "Leaf Level Ticking Thread": "BeefMC Level Ticking Thread",
        "Leaf IO Thread": "BeefMC IO Thread",
        'LogManager.getLogger("Leaf")': 'LogManager.getLogger("BeefMC")',
        'LogManager.getLogger("Leaf Vanilla Bug Fix")': 'LogManager.getLogger("BeefMC Vanilla Bug Fix")',
        "Reloading Leaf config...": "Reloading BeefMC config...",
        "Increasing max-threads in Leaf config may help.": "Increasing max-threads in BeefMC config may help.",
        "Please enable it in your Leaf configuration to use this command.": "Please enable it in your BeefMC configuration to use this command.",
        "Leaf Vanilla Bug Fix": "BeefMC Vanilla Bug Fix",
        "Read Leaf docs before using!": "Read the BeefMC README before using!",
        "使用前请阅读 Leaf 文档!": "使用前请阅读 BeefMC README!",
    }
    changed = False
    for before, after in replacements.items():
        if before in content:
            content = content.replace(before, after)
            changed = True
    return content, changed


def _replace_leaf_version_fetcher(content: str) -> tuple[str, bool]:
    original = content
    content = re.sub(r'    public static final String API_URL = .*?;\n', "", content)
    content = re.sub(r'    public static final String USER_AGENT = .*?;\n', "", content)
    content = content.replace('"https://www.leafmc.one/download"', '"https://github.com/Sawlyer/BeefMC/releases"')
    content = content.replace('"Winds Studio"', '"BeefMC"')
    content = content.replace('"Leaf"', '"BeefMC"')
    content = content.replace('"Winds-Studio"', '"Sawlyer"')
    content = re.sub(
        r'        super\([\s\S]*?\n        \);',
        '        super(DOWNLOAD_PAGE, "BeefMC", "BeefMC", "Sawlyer", "BeefMC", ApiType.GITHUB);',
        content,
        count=1,
    )
    return content, content != original or '"https://github.com/Sawlyer/BeefMC/releases"' in content


def _replace_leaf_system_properties(content: str) -> tuple[str, bool]:
    original = content
    property_names = (
        "disable-vanilla-profiler",
        "enableFMA",
        "enable-io-uring",
        "enable-base64coder-warning",
        "disable-vanilla-debug-feature",
        "async-tracker-protocol-lib-fix",
    )
    for name in property_names:
        content = content.replace(
            f'Boolean.getBoolean("Leaf.{name}")',
            f'Boolean.getBoolean("BeefMC.{name}")',
        )
    content = content.replace(
        "https://www.leafmc.one/docs/config/system-properties#dleaf-disable-vanilla-profiler",
        "https://github.com/Sawlyer/BeefMC#configuration",
    )
    return content, content != original or "BeefMC.disable-vanilla-profiler" in content


def _replace_build_metadata(content: str) -> tuple[str, bool]:
    replacements = {
        '"Implementation-Title" to "Paper"': '"Implementation-Title" to "BeefMC"',
        '"Implementation-Title" to "CraftBukkit"': '"Implementation-Title" to "BeefMC"',
        '"Implementation-Title" to "PaperSpigot"': '"Implementation-Title" to "BeefMC"',
        '"Implementation-Title" to "PandaSpigot"': '"Implementation-Title" to "BeefMC"',
          '"Implementation-Title" to "Leaf"': '"Implementation-Title" to "BeefMC"',
        '"Specification-Title" to "Paper"': '"Specification-Title" to "BeefMC"',
        '"Specification-Title" to "PaperSpigot"': '"Specification-Title" to "BeefMC"',
        '"Specification-Title" to "PandaSpigot"': '"Specification-Title" to "BeefMC"',
          '"Specification-Title" to "Leaf"': '"Specification-Title" to "BeefMC"',
        '"Specification-Vendor" to "Paper Team"': '"Specification-Vendor" to "BeefMC"',
          '"Specification-Vendor" to "Winds Studio"': '"Specification-Vendor" to "BeefMC"',
        '"Brand-Name" to "Paper"': '"Brand-Name" to "BeefMC"',
          '"Brand-Name" to "Leaf"': '"Brand-Name" to "BeefMC"',
        "<Implementation-Title>Paper</Implementation-Title>": "<Implementation-Title>BeefMC</Implementation-Title>",
        "<Implementation-Title>CraftBukkit</Implementation-Title>": "<Implementation-Title>BeefMC</Implementation-Title>",
        "<Implementation-Title>PaperSpigot</Implementation-Title>": "<Implementation-Title>BeefMC</Implementation-Title>",
        "<Implementation-Title>PandaSpigot</Implementation-Title>": "<Implementation-Title>BeefMC</Implementation-Title>",
          "<Implementation-Title>Leaf</Implementation-Title>": "<Implementation-Title>BeefMC</Implementation-Title>",
        "<Specification-Title>Paper</Specification-Title>": "<Specification-Title>BeefMC</Specification-Title>",
        "<Specification-Title>PaperSpigot</Specification-Title>": "<Specification-Title>BeefMC</Specification-Title>",
        "<Specification-Title>PandaSpigot</Specification-Title>": "<Specification-Title>BeefMC</Specification-Title>",
          "<Specification-Title>Leaf</Specification-Title>": "<Specification-Title>BeefMC</Specification-Title>",
        "<Brand-Name>Paper</Brand-Name>": "<Brand-Name>BeefMC</Brand-Name>",
          "<Brand-Name>Leaf</Brand-Name>": "<Brand-Name>BeefMC</Brand-Name>",
    }
    changed = False
    for before, after in replacements.items():
        if before in content:
            content = content.replace(before, after)
            changed = True
    branded_markers = (
        '"Implementation-Title" to "BeefMC"',
        '"Specification-Title" to "BeefMC"',
        '"Specification-Vendor" to "BeefMC"',
        '"Brand-Name" to "BeefMC"',
        "<Implementation-Title>BeefMC</Implementation-Title>",
        "<Specification-Title>BeefMC</Specification-Title>",
        "<Brand-Name>BeefMC</Brand-Name>",
    )
    return content, changed or any(marker in content for marker in branded_markers)


def _replace_gradle_project_names(content: str, family: str) -> tuple[str, bool]:
    original = content
    if family == "legacy":
        replacements = {
            'setupSubproject("pandaspigot-server", "PandaSpigot-Server")': 'setupSubproject("beefmc-server", "BeefMC-Server")',
            'setupSubproject("pandaspigot-api", "PandaSpigot-API")': 'setupSubproject("beefmc-api", "BeefMC-API")',
        }
        for before, after in replacements.items():
            content = content.replace(before, after)
        found = all(
            f'setupSubproject("beefmc-{module}", "BeefMC-{directory}")' in content
            for module, directory in (("server", "Server"), ("api", "API"))
        )
    elif family == "modern":
        content = content.replace("Leaf start - project setup", "BeefMC start - project setup")
        content = content.replace("Leaf end - project setup", "BeefMC end - project setup")
        content = content.replace("Leaf", "BeefMC")
        content = content.replace("https://www.leafmc.one/download", "https://github.com/Sawlyer/BeefMC/releases")
        content = content.replace(
            "https://github.com/PaperMC/Paper/blob/main/CONTRIBUTING.md",
            "CONTRIBUTING.md",
        )
        content = content.replace("Paper forks", "Minecraft server forks")
        content = content.replace('rootProject.name = "leaf"', 'rootProject.name = "beefmc"')
        content = re.sub(
            r'for \(name in listOf\("leaf-api", "leaf-server"\)\) \{.*?\n\}',
            'for ((projectName, directoryName) in listOf("beefmc-api" to "leaf-api", "beefmc-server" to "leaf-server")) {\n'
            '    include(projectName)\n'
            '    project(":$projectName").projectDir = file(directoryName)\n'
            '}',
            content,
            flags=re.DOTALL,
        )
        found = 'rootProject.name = "beefmc"' in content and '"beefmc-server" to "leaf-server"' in content
    else:
        return content, False
    return content, content != original or found


def _replace_legacy_jar_script(content: str) -> tuple[str, bool]:
    replacements = {
        "Failed to build Paperclip jar.": "Failed to build BeefMC server jar.",
        "paperclip.jar": "beefmc-1.8.8.jar",
    }
    changed = False
    for before, after in replacements.items():
        if before in content:
            content = content.replace(before, after)
            changed = True
    return content, changed or "beefmc-1.8.8.jar" in content


def _replace_gradle_build(content: str, family: str) -> tuple[str, bool]:
    original = content
    content, metadata_found = _replace_build_metadata(content)
    dependencies = {
        "legacy": {
            'project(":pandaspigot-api")': 'project(":beefmc-api")',
            'project(":pandaspigot-server")': 'project(":beefmc-server")',
        },
        "modern": {
            'project(":leaf-api")': 'project(":beefmc-api")',
            'project(":leaf-server")': 'project(":beefmc-server")',
        },
    }.get(family, {})
    for before, after in dependencies.items():
        content = content.replace(before, after)
    if family == "legacy":
        content = content.replace("pandaspigot-api", "beefmc-api")
        content = content.replace("pandaspigot-server", "beefmc-server")
    return content, content != original or metadata_found or 'project(":beefmc-api")' in content


def _source_files(source_root: Path) -> list[Path]:
    names = {
        "CraftServer.java",
        "MinecraftServer.java",
        "WatchdogThread.java",
        "ServerBuildInfoImpl.java",
        "ServerWatchdog.java",
        "LeafConfig.java",
        "LeafGlobalConfig.java",
        "LeafCommand.java",
        "LeafCommands.java",
        "ReloadCommand.java",
        "AsyncPathProcessor.java",
        "AsyncPlayerDataSaving.java",
        "AsyncTracker.java",
        "LeafVersionFetcher.java",
        "MSPTCommand.java",
        "SpawnerSettings.java",
        "RegionFormatConfig.java",
        "ShutdownExecutors.java",
        "MCBugFix.java",
        "LeafConstants.java",
        "SparklyPaperServerLevelTickExecutorThreadFactory.java",
        "CraftDefaultPermissions.java",
        "LeafServerConfigProvider.java",
        "build.gradle",
        "build.gradle.kts",
        "paperclip.gradle.kts",
        "settings.gradle.kts",
        "paperclip.sh",
        "pom.xml",
    }
    excluded = {".git", ".gradle", "build", "target", "node_modules"}
    return sorted(
        path
        for path in source_root.rglob("*")
        if path.is_file()
        and path.name in names
        and not any(part in excluded for part in path.relative_to(source_root).parts)
    )


def apply_rebrand(source_root: Path, version: str, family: str) -> list[Change]:
    source_root = source_root.resolve()
    if not source_root.is_dir():
        raise ValueError(f"source root does not exist: {source_root}")

    transforms = {
        "CraftServer.java": _replace_server_name,
        "MinecraftServer.java": _replace_server_mod_name,
        "WatchdogThread.java": _replace_watchdog,
        "ServerWatchdog.java": _replace_watchdog,
        "ServerBuildInfoImpl.java": lambda content: _replace_build_info_fallback(content, family),
        "build.gradle": lambda content: _replace_gradle_build(content, family),
        "build.gradle.kts": lambda content: _replace_gradle_build(content, family),
        "paperclip.gradle.kts": lambda content: _replace_gradle_build(content, family),
        "settings.gradle.kts": lambda content: _replace_gradle_project_names(content, family),
        "paperclip.sh": _replace_legacy_jar_script,
        "pom.xml": _replace_build_metadata,
    }
    leaf_transforms = {
        "LeafConfig.java": _replace_leaf_config,
        "LeafGlobalConfig.java": _replace_leaf_global_config,
        "LeafCommand.java": _replace_leaf_command,
        "LeafCommands.java": _replace_leaf_command_registration,
        "ReloadCommand.java": _replace_leaf_runtime_strings,
        "AsyncPathProcessor.java": _replace_leaf_runtime_strings,
        "AsyncPlayerDataSaving.java": _replace_leaf_runtime_strings,
        "AsyncTracker.java": _replace_leaf_runtime_strings,
        "LeafVersionFetcher.java": _replace_leaf_version_fetcher,
        "MSPTCommand.java": _replace_leaf_runtime_strings,
        "SpawnerSettings.java": _replace_leaf_runtime_strings,
        "RegionFormatConfig.java": _replace_leaf_runtime_strings,
        "ShutdownExecutors.java": _replace_leaf_runtime_strings,
        "MCBugFix.java": _replace_leaf_runtime_strings,
        "LeafConstants.java": _replace_leaf_system_properties,
        "SparklyPaperServerLevelTickExecutorThreadFactory.java": _replace_leaf_runtime_strings,
        "CraftDefaultPermissions.java": _replace_leaf_permission_root,
        "LeafServerConfigProvider.java": lambda content: (
            content.replace('"leaf/"', '"beefmc/"'),
            '"beefmc/"' in content,
        ),
    }
    changes: list[Change] = []
    brand_markers = 0
    for path in _source_files(source_root):
        original = path.read_text(encoding="utf-8")
        transform = leaf_transforms.get(path.name) if family == "modern" else None
        transform = transform or transforms.get(path.name)
        if transform is None:
            continue
        transformed, found = transform(original)
        if found:
            brand_markers += 1
        if transformed != original:
            path.write_text(transformed, encoding="utf-8", newline="")
            changes.append(Change(path, original, transformed))

    if not brand_markers:
        raise ValueError(
            f"no supported branding markers found for Minecraft {version} ({family}); "
            "source may not have been patched yet or upstream layout changed"
        )
    return changes


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply BeefMC runtime and build metadata branding")
    subparsers = parser.add_subparsers(dest="command", required=True)
    apply_parser = subparsers.add_parser("apply")
    apply_parser.add_argument("--source-root", type=Path, required=True)
    apply_parser.add_argument("--version", required=True)
    apply_parser.add_argument("--family", choices=("legacy", "modern"), required=True)
    args = parser.parse_args()
    try:
        changes = apply_rebrand(args.source_root, args.version, args.family)
        print(
            f"BeefMC branding ready for Minecraft {args.version} ({args.family}); "
            f"updated {len(changes)} source/build files."
        )
        return 0
    except (OSError, UnicodeError, ValueError) as error:
        print(f"rebrand: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
