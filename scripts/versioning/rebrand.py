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


def _replace_beefmc_version_command(content: str) -> tuple[str, bool]:
    marker = "BEEFMC_RELEASE_STATUS"
    if marker in content:
        return content, True
    execute_anchor = "            sendVersion(sender);"
    class_anchor = "public class VersionCommand extends BukkitCommand {"
    import_anchor = "import org.bukkit.plugin.Plugin;"
    helper_anchor = "    private void describeToSender(@NotNull Plugin plugin, @NotNull CommandSender sender) {"
    brigadier = "public class PaperVersionCommand {" in content
    if brigadier:
        class_anchor = "public class PaperVersionCommand {"
        execute_anchor = "        sendVersion(context.getSource().getSender());"
        helper_anchor = "    private int serverVersion("
    if any(anchor not in content for anchor in (execute_anchor, class_anchor, import_anchor, helper_anchor)):
        return content, False

    imports = """\nimport net.kyori.adventure.text.Component;
import net.kyori.adventure.text.format.NamedTextColor;
import java.io.ByteArrayOutputStream;
import java.net.HttpURLConnection;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;"""
    fields = r'''
    private static final Pattern RELEASE_TAG = Pattern.compile("\\\"tag_name\\\"\\s*:\\s*\\\"(v(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*))\\\"");
    private static volatile String BEEFMC_RELEASE_STATUS = "checking";
    private static boolean beefmcReleaseCheckStarted;
    private static long beefmcReleaseCheckedAt;
    private static final long BEEFMC_RELEASE_CACHE_MILLIS = 600000L;
    private static final List<CommandSender> BEEFMC_RELEASE_WAITERS = new ArrayList<CommandSender>();
'''
    call = "            checkBeefMCReleaseAsync(sender);\n"
    helpers = r'''
    private static void checkBeefMCReleaseAsync(@NotNull CommandSender sender) {
        boolean startCheck = false;
        String status;
        synchronized (VersionCommand.class) {
            status = BEEFMC_RELEASE_STATUS;
            if (!"checking".equals(status) && System.currentTimeMillis() - beefmcReleaseCheckedAt > BEEFMC_RELEASE_CACHE_MILLIS) {
                status = "checking";
                BEEFMC_RELEASE_STATUS = status;
            }
            if ("checking".equals(status)) {
                BEEFMC_RELEASE_WAITERS.add(sender);
                if (!beefmcReleaseCheckStarted) {
                    beefmcReleaseCheckStarted = true;
                    startCheck = true;
                }
            }
        }
        if (!"checking".equals(status)) {
            sendBeefMCReleaseStatus(sender, status);
            return;
        }
        sender.sendMessage(Component.text("Checking for BeefMC releases in the background.", NamedTextColor.GRAY));
        if (!startCheck) {
            return;
        }
        Thread checker = new Thread(() -> {
            String result = "unavailable";
            String minecraft = System.getProperty("beefmc.minecraft.version", "");
            String current = System.getProperty("beefmc.release.tag", "");
            if (!minecraft.isEmpty()) {
                HttpURLConnection connection = null;
                try {
                    connection = (HttpURLConnection) URI.create("https://api.github.com/repos/Sawlyer/BeefMC/releases/latest").toURL().openConnection();
                    connection.setConnectTimeout(5000);
                    connection.setReadTimeout(5000);
                    connection.setRequestProperty("Accept", "application/vnd.github+json");
                    connection.setRequestProperty("User-Agent", "BeefMC-Version-Check/1.0");
                    if (connection.getResponseCode() == HttpURLConnection.HTTP_OK) {
                        ByteArrayOutputStream response = new ByteArrayOutputStream();
                        byte[] buffer = new byte[4096];
                        try (java.io.InputStream input = connection.getInputStream()) {
                            int length;
                            while ((length = input.read(buffer)) != -1 && response.size() + length <= 131072) {
                                response.write(buffer, 0, length);
                            }
                        }
                        String json = new String(response.toByteArray(), StandardCharsets.UTF_8);
                        Matcher matcher = RELEASE_TAG.matcher(json);
                        if (matcher.find()) {
                            String latest = matcher.group(1);
                            String asset = "\\\"name\\\"\\s*:\\s*\\\"BeefMC-" + Pattern.quote(minecraft) + "-" + Pattern.quote(latest) + "\\.jar\\\"";
                            String checksum = asset.substring(0, asset.length() - 2) + "\\.sha256\\\"";
                            if (Pattern.compile(asset).matcher(json).find() && Pattern.compile(checksum).matcher(json).find()) {
                                result = current.isEmpty() ? "latest:" + latest
                                    : compareBeefMCReleaseTags(latest, current) > 0 ? "available:" + latest : "current:" + current;
                            }
                        }
                    }
                } catch (Exception ignored) {
                    result = "unavailable";
                } finally {
                    if (connection != null) {
                        connection.disconnect();
                    }
                }
            }
            List<CommandSender> waiters;
            synchronized (VersionCommand.class) {
                BEEFMC_RELEASE_STATUS = result;
                beefmcReleaseCheckedAt = System.currentTimeMillis();
                beefmcReleaseCheckStarted = false;
                waiters = new ArrayList<CommandSender>(BEEFMC_RELEASE_WAITERS);
                BEEFMC_RELEASE_WAITERS.clear();
            }
            for (CommandSender waiter : waiters) {
                sendBeefMCReleaseStatus(waiter, result);
            }
        }, "BeefMC-release-check");
        checker.setDaemon(true);
        checker.start();
    }

    private static void sendBeefMCReleaseStatus(@NotNull CommandSender sender, String status) {
        if (status.startsWith("available:")) {
            sender.sendMessage(Component.text("BeefMC update " + status.substring("available:".length())
                + " is available for Minecraft " + System.getProperty("beefmc.minecraft.version", "unknown")
                + "." + beefmcUpdateInstallationMessage(), NamedTextColor.GREEN));
        } else if (status.startsWith("current:")) {
            sender.sendMessage(Component.text("BeefMC is up to date (" + status.substring("current:".length()) + ").", NamedTextColor.GRAY));
        } else if (status.startsWith("latest:")) {
            String message = "Latest stable BeefMC release is " + status.substring("latest:".length()) + ". Current JAR version is unknown";
            if (!Boolean.parseBoolean(System.getProperty("beefmc.launcher", "false"))) {
                message += "; use BeefMC-Launcher.jar to compare and install it at startup.";
            } else if (!Boolean.parseBoolean(System.getProperty("beefmc.auto-update", "true"))) {
                message += "; automatic updates are disabled for this server.";
            } else {
                message += "; launcher will compare and install it at next startup.";
            }
            sender.sendMessage(Component.text(message, NamedTextColor.YELLOW));
        } else {
            sender.sendMessage(Component.text("BeefMC release check unavailable. The launcher will retry at next startup.", NamedTextColor.GRAY));
        }
    }

    private static String beefmcUpdateInstallationMessage() {
        if (!Boolean.parseBoolean(System.getProperty("beefmc.launcher", "false"))) {
            return " Use BeefMC-Launcher.jar to install updates automatically.";
        }
        return Boolean.parseBoolean(System.getProperty("beefmc.auto-update", "true"))
            ? " It will install at the next launcher start."
            : " Automatic updates are disabled for this server.";
    }

    private static int compareBeefMCReleaseTags(String first, String second) {
        int[] left = parseBeefMCReleaseTag(first);
        int[] right = parseBeefMCReleaseTag(second);
        if (left == null || right == null) {
            return left == null ? (right == null ? 0 : -1) : 1;
        }
        for (int index = 0; index < left.length; index++) {
            int compare = Integer.compare(left[index], right[index]);
            if (compare != 0) {
                return compare;
            }
        }
        return 0;
    }

    private static int[] parseBeefMCReleaseTag(String tag) {
        if (tag == null || !tag.matches("v(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)")) {
            return null;
        }
        try {
            String[] parts = tag.substring(1).split("\\.");
            return new int[] { Integer.parseInt(parts[0]), Integer.parseInt(parts[1]), Integer.parseInt(parts[2]) };
        } catch (NumberFormatException exception) {
            return null;
        }
    }
'''
    if brigadier:
        call = "        checkBeefMCReleaseAsync(context.getSource().getSender());\n"
        helpers = helpers.replace("@NotNull CommandSender", "CommandSender").replace("VersionCommand.class", "PaperVersionCommand.class")
    imports = "".join("\n" + line for line in imports.splitlines() if line and line not in content)
    content = content.replace(import_anchor, import_anchor + imports)
    content = content.replace(class_anchor, class_anchor + fields)
    content = content.replace(execute_anchor, call + execute_anchor)
    content = content.replace(helper_anchor, helpers + '\n' + helper_anchor)
    return content, marker in content

def _replace_beefmc_legacy_version_command(content: str) -> tuple[str, bool]:
    marker = "BEEFMC_RELEASE_STATUS"
    if marker in content:
        return content, True
    execute_anchor = "            sendVersion(sender);"
    class_anchor = "public class VersionCommand extends BukkitCommand {"
    import_anchor = "import org.bukkit.plugin.Plugin;"
    helper_anchor = "    private void describeToSender(Plugin plugin, CommandSender sender) {"
    if execute_anchor not in content or class_anchor not in content or import_anchor not in content:
        return content, False
    if helper_anchor not in content:
        helper_anchor = "    private void describeToSender(@NotNull Plugin plugin, @NotNull CommandSender sender) {"
    if helper_anchor not in content:
        return content, False

    imports = """\nimport java.io.ByteArrayOutputStream;
import java.net.HttpURLConnection;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;"""
    fields = r'''
    private static final Pattern RELEASE_TAG = Pattern.compile("\\\"tag_name\\\"\\s*:\\s*\\\"(v(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*))\\\"");
    private static volatile String BEEFMC_RELEASE_STATUS = "checking";
    private static boolean beefmcReleaseCheckStarted;
    private static long beefmcReleaseCheckedAt;
    private static final long BEEFMC_RELEASE_CACHE_MILLIS = 600000L;
    private static final List<CommandSender> BEEFMC_RELEASE_WAITERS = new ArrayList<CommandSender>();
'''
    helpers = r'''
    private static void checkBeefMCReleaseAsync(CommandSender sender) {
        boolean startCheck = false;
        String status;
        synchronized (VersionCommand.class) {
            status = BEEFMC_RELEASE_STATUS;
            if (!"checking".equals(status) && System.currentTimeMillis() - beefmcReleaseCheckedAt > BEEFMC_RELEASE_CACHE_MILLIS) {
                status = "checking";
                BEEFMC_RELEASE_STATUS = status;
            }
            if ("checking".equals(status)) {
                BEEFMC_RELEASE_WAITERS.add(sender);
                if (!beefmcReleaseCheckStarted) {
                    beefmcReleaseCheckStarted = true;
                    startCheck = true;
                }
            }
        }
        if (!"checking".equals(status)) {
            sendBeefMCReleaseStatus(sender, status);
            return;
        }
        sender.sendMessage("Checking for BeefMC releases in the background.");
        if (!startCheck) {
            return;
        }
        Thread checker = new Thread(() -> {
            String result = "unavailable";
            String minecraft = System.getProperty("beefmc.minecraft.version", "");
            String current = System.getProperty("beefmc.release.tag", "");
            if (!minecraft.isEmpty()) {
                HttpURLConnection connection = null;
                try {
                    connection = (HttpURLConnection) URI.create("https://api.github.com/repos/Sawlyer/BeefMC/releases/latest").toURL().openConnection();
                    connection.setConnectTimeout(5000);
                    connection.setReadTimeout(5000);
                    connection.setRequestProperty("Accept", "application/vnd.github+json");
                    connection.setRequestProperty("User-Agent", "BeefMC-Version-Check/1.0");
                    if (connection.getResponseCode() == HttpURLConnection.HTTP_OK) {
                        ByteArrayOutputStream response = new ByteArrayOutputStream();
                        byte[] buffer = new byte[4096];
                        try (java.io.InputStream input = connection.getInputStream()) {
                            int length;
                            while ((length = input.read(buffer)) != -1 && response.size() + length <= 131072) {
                                response.write(buffer, 0, length);
                            }
                        }
                        String json = new String(response.toByteArray(), StandardCharsets.UTF_8);
                        Matcher matcher = RELEASE_TAG.matcher(json);
                        if (matcher.find()) {
                            String latest = matcher.group(1);
                            String asset = "\\\"name\\\"\\s*:\\s*\\\"BeefMC-" + Pattern.quote(minecraft) + "-" + Pattern.quote(latest) + "\\.jar\\\"";
                            String checksum = asset.substring(0, asset.length() - 2) + "\\.sha256\\\"";
                            if (Pattern.compile(asset).matcher(json).find() && Pattern.compile(checksum).matcher(json).find()) {
                                result = current.isEmpty() ? "latest:" + latest
                                    : compareBeefMCReleaseTags(latest, current) > 0 ? "available:" + latest : "current:" + current;
                            }
                        }
                    }
                } catch (Exception ignored) {
                    result = "unavailable";
                } finally {
                    if (connection != null) {
                        connection.disconnect();
                    }
                }
            }
            List<CommandSender> waiters;
            synchronized (VersionCommand.class) {
                BEEFMC_RELEASE_STATUS = result;
                beefmcReleaseCheckedAt = System.currentTimeMillis();
                beefmcReleaseCheckStarted = false;
                waiters = new ArrayList<CommandSender>(BEEFMC_RELEASE_WAITERS);
                BEEFMC_RELEASE_WAITERS.clear();
            }
            for (CommandSender waiter : waiters) {
                sendBeefMCReleaseStatus(waiter, result);
            }
        }, "BeefMC-release-check");
        checker.setDaemon(true);
        checker.start();
    }

    private static void sendBeefMCReleaseStatus(CommandSender sender, String status) {
        if (status.startsWith("available:")) {
            sender.sendMessage("BeefMC update " + status.substring("available:".length())
                + " is available for Minecraft " + System.getProperty("beefmc.minecraft.version", "unknown")
                + "." + beefmcUpdateInstallationMessage());
        } else if (status.startsWith("current:")) {
            sender.sendMessage("BeefMC is up to date (" + status.substring("current:".length()) + ").");
        } else if (status.startsWith("latest:")) {
            String message = "Latest stable BeefMC release is " + status.substring("latest:".length()) + ". Current JAR version is unknown";
            if (!Boolean.parseBoolean(System.getProperty("beefmc.launcher", "false"))) {
                message += "; use BeefMC-Launcher.jar to compare and install it at startup.";
            } else if (!Boolean.parseBoolean(System.getProperty("beefmc.auto-update", "true"))) {
                message += "; automatic updates are disabled for this server.";
            } else {
                message += "; launcher will compare and install it at next startup.";
            }
            sender.sendMessage(message);
        } else {
            sender.sendMessage("BeefMC release check unavailable. The launcher will retry at next startup.");
        }
    }

    private static String beefmcUpdateInstallationMessage() {
        if (!Boolean.parseBoolean(System.getProperty("beefmc.launcher", "false"))) {
            return " Use BeefMC-Launcher.jar to install updates automatically.";
        }
        return Boolean.parseBoolean(System.getProperty("beefmc.auto-update", "true"))
            ? " It will install at the next launcher start."
            : " Automatic updates are disabled for this server.";
    }

    private static int compareBeefMCReleaseTags(String first, String second) {
        int[] left = parseBeefMCReleaseTag(first);
        int[] right = parseBeefMCReleaseTag(second);
        if (left == null || right == null) {
            return left == null ? (right == null ? 0 : -1) : 1;
        }
        for (int index = 0; index < left.length; index++) {
            int compare = Integer.compare(left[index], right[index]);
            if (compare != 0) {
                return compare;
            }
        }
        return 0;
    }

    private static int[] parseBeefMCReleaseTag(String tag) {
        if (tag == null || !tag.matches("v(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)")) {
            return null;
        }
        try {
            String[] parts = tag.substring(1).split("\\.");
            return new int[] { Integer.parseInt(parts[0]), Integer.parseInt(parts[1]), Integer.parseInt(parts[2]) };
        } catch (NumberFormatException exception) {
            return null;
        }
    }
'''
    content = content.replace(import_anchor, import_anchor + imports)
    content = content.replace(class_anchor, class_anchor + fields)
    content = content.replace(execute_anchor, "            checkBeefMCReleaseAsync(sender);\n" + execute_anchor)
    content = content.replace(helper_anchor, helpers + "\n" + helper_anchor)
    return content, marker in content

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
        found = (
            'rootProject.name = "beefmc"' in content
            and 'include("beefmc-api", "beefmc-server")' in content
        )
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
        "modern": {},
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
        "VersionCommand.java",
        "PaperVersionCommand.java",
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
    legacy_transforms = {
        "VersionCommand.java": _replace_beefmc_legacy_version_command,
    }
    changes: list[Change] = []
    brand_markers = 0
    for path in _source_files(source_root):
        original = path.read_text(encoding="utf-8")
        if path.name in {"VersionCommand.java", "PaperVersionCommand.java"}:
            transform = _replace_beefmc_version_command if family == "modern" else legacy_transforms.get(path.name)
        else:
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
