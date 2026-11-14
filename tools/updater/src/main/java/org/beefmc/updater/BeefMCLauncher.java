package org.beefmc.updater;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Optional;

public final class BeefMCLauncher {
    private BeefMCLauncher() {
    }

    public static void main(String[] args) {
        int exitCode;
        try {
            exitCode = launch(args);
        } catch (Exception exception) {
            System.err.println("BeefMC launcher: " + exception.getMessage());
            exitCode = 1;
        }
        if (exitCode != 0) {
            System.exit(exitCode);
        }
    }

    static int launch(String[] args) throws Exception {
        LaunchOptions options = LaunchOptions.parse(args);
        Path serverDirectory = Paths.get("").toAbsolutePath().normalize();
        Path serverJar = options.serverJar.isAbsolute() ? options.serverJar.normalize() : serverDirectory.resolve(options.serverJar).normalize();
        if (UpdateInstaller.recoverBackup(serverJar)) {
            System.err.println("Recovered the previous BeefMC server JAR after an interrupted update.");
        }
        if (!Files.isRegularFile(serverJar)) {
            throw new IOException("Server JAR not found: " + serverJar);
        }

        LauncherSettings settings;
        try {
            settings = LauncherSettings.load(serverDirectory, options.autoUpdateOverride);
        } catch (IOException invalidSettings) {
            System.err.println("BeefMC updater settings invalid; automatic updates disabled for this startup: " + invalidSettings.getMessage());
            settings = LauncherSettings.disabled();
        }
        ReleaseClient client = new ReleaseClient();
        UpdateInstaller installer = new UpdateInstaller(5000, 15000);
        String installedTag = System.getProperty("beefmc.release.tag", "");
        try {
            if (settings.isAutoUpdate()) {
                Optional<ReleaseClient.ReleaseAsset> latest = client.latest(options.minecraftVersion);
                if (latest.isPresent()) {
                    ReleaseClient.ReleaseAsset release = latest.get();
                    UpdateInstaller.UpdateResult result = installer.install(serverJar, release, true);
                    if (result.getOutcome() == UpdateInstaller.Outcome.INSTALLED
                        || result.getOutcome() == UpdateInstaller.Outcome.ALREADY_CURRENT) {
                        installedTag = release.getTag();
                        System.out.println("BeefMC release " + release.getTag() + " ready for Minecraft " + options.minecraftVersion);
                    }
                }
            }
        } catch (IOException | RuntimeException updateFailure) {
            System.err.println("BeefMC update check failed; starting the installed server: " + updateFailure.getMessage());
        }
        if (installedTag.isEmpty()) {
            installedTag = UpdateInstaller.installedReleaseTag(serverJar);
        }

        UpdateInstaller.validateDownloadedJar(serverJar);
        List<String> command = new ArrayList<String>();
        command.add(Paths.get(System.getProperty("java.home"), "bin", isWindows() ? "java.exe" : "java").toString());
        command.addAll(options.jvmArgs);
        command.add("-Dbeefmc.launcher=true");
        command.add("-Dbeefmc.minecraft.version=" + options.minecraftVersion);
        command.add("-Dbeefmc.auto-update=" + settings.isAutoUpdate());
        if (!installedTag.isEmpty()) {
            command.add("-Dbeefmc.release.tag=" + installedTag);
        }
        command.add("-jar");
        command.add(serverJar.toString());
        command.addAll(options.serverArgs);
        Process child = new ProcessBuilder(command).directory(serverDirectory.toFile()).inheritIO().start();
        return child.waitFor();
    }

    private static boolean isWindows() {
        return System.getProperty("os.name", "").toLowerCase().contains("win");
    }

    static final class LaunchOptions {
        final String minecraftVersion;
        final Path serverJar;
        final Boolean autoUpdateOverride;
        final List<String> jvmArgs;
        final List<String> serverArgs;

        private LaunchOptions(String minecraftVersion, Path serverJar, Boolean autoUpdateOverride, List<String> jvmArgs, List<String> serverArgs) {
            this.minecraftVersion = minecraftVersion;
            this.serverJar = serverJar;
            this.autoUpdateOverride = autoUpdateOverride;
            this.jvmArgs = jvmArgs;
            this.serverArgs = serverArgs;
        }

        static LaunchOptions parse(String[] args) {
            String minecraftVersion = null;
            Path serverJar = null;
            Boolean autoUpdateOverride = null;
            int separator = -1;
            for (int index = 0; index < args.length; index++) {
                if ("--".equals(args[index])) {
                    separator = index;
                    break;
                }
            }
            int end = separator < 0 ? args.length : separator;
            for (int index = 0; index < end; index++) {
                String argument = args[index];
                if ("--minecraft-version".equals(argument) && index + 1 < end) {
                    minecraftVersion = args[++index];
                } else if ("--server-jar".equals(argument) && index + 1 < end) {
                    serverJar = Paths.get(args[++index]);
                } else if ("--auto-update".equals(argument) && index + 1 < end) {
                    String setting = args[++index];
                    if (!"true".equalsIgnoreCase(setting) && !"false".equalsIgnoreCase(setting)) {
                        throw new IllegalArgumentException("--auto-update must be true or false");
                    }
                    autoUpdateOverride = Boolean.parseBoolean(setting);
                } else {
                    throw new IllegalArgumentException("Unknown or incomplete launcher argument: " + argument);
                }
            }
            if (minecraftVersion == null || serverJar == null) {
                throw new IllegalArgumentException("Usage: java -jar BeefMC-Launcher.jar --minecraft-version <version> --server-jar <path> [-- <server arguments>]");
            }
            if (!ReleaseClient.supports(minecraftVersion)) {
                throw new IllegalArgumentException("Unsupported Minecraft version: " + minecraftVersion);
            }
            List<String> jvmArgs = new ArrayList<String>();
            List<String> serverArgs = new ArrayList<String>();
            if (separator >= 0) {
                for (String argument : Arrays.copyOfRange(args, separator + 1, args.length)) {
                    if (isJvmArgument(argument)) {
                        jvmArgs.add(argument);
                    } else {
                        serverArgs.add(argument);
                    }
                }
            }
            return new LaunchOptions(minecraftVersion, serverJar, autoUpdateOverride, jvmArgs, serverArgs);
        }

        private static boolean isJvmArgument(String argument) {
            return argument.startsWith("-X") || argument.startsWith("-D") || argument.startsWith("-XX:")
                || argument.startsWith("-javaagent:") || argument.startsWith("-agentlib:")
                || argument.startsWith("--add-") || argument.startsWith("--enable-")
                || argument.startsWith("--module-path") || argument.startsWith("--patch-module");
        }
    }
}
