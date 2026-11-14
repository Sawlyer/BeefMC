package org.beefmc.updater;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

final class BeefMCLauncherTest {
    @Test
    void parsesTargetJarAndPreservesServerArgsIncludingSpaces() {
        BeefMCLauncher.LaunchOptions options = BeefMCLauncher.LaunchOptions.parse(new String[] {
            "--minecraft-version", "1.21.11", "--server-jar", "server folder/server.jar", "--", "-Xmx3G", "-Dexample=value", "--nogui", "world with spaces"
        });

        assertEquals("1.21.11", options.minecraftVersion);
        assertEquals("server folder" + java.io.File.separator + "server.jar", options.serverJar.toString());
        assertEquals(2, options.jvmArgs.size());
        assertEquals("-Xmx3G", options.jvmArgs.get(0));
        assertEquals(2, options.serverArgs.size());
        assertEquals("world with spaces", options.serverArgs.get(1));
    }

    @Test
    void acceptsEverySupportedVersionAndRejectsUnknownTargets() {
        for (String version : new String[] { "1.8.8", "1.21.11", "26.1.2", "26.3" }) {
            BeefMCLauncher.LaunchOptions.parse(new String[] { "--minecraft-version", version, "--server-jar", "server.jar" });
        }
        assertThrows(IllegalArgumentException.class, () -> BeefMCLauncher.LaunchOptions.parse(new String[] {
            "--minecraft-version", "26.2", "--server-jar", "server.jar"
        }));
    }

    @Test
    void requiresVersionAndServerJar() {
        assertThrows(IllegalArgumentException.class, () -> BeefMCLauncher.LaunchOptions.parse(new String[] { "--minecraft-version", "26.3" }));
        assertThrows(IllegalArgumentException.class, () -> BeefMCLauncher.LaunchOptions.parse(new String[] { "--server-jar", "server.jar" }));
    }

    @Test
    void acceptsAutomaticUpdateOverride() {
        BeefMCLauncher.LaunchOptions options = BeefMCLauncher.LaunchOptions.parse(new String[] {
            "--minecraft-version", "26.3", "--server-jar", "server.jar", "--auto-update", "false"
        });
        assertEquals(Boolean.FALSE, options.autoUpdateOverride);
        assertThrows(IllegalArgumentException.class, () -> BeefMCLauncher.LaunchOptions.parse(new String[] {
            "--minecraft-version", "26.3", "--server-jar", "server.jar", "--auto-update", "sometimes"
        }));
    }
}
