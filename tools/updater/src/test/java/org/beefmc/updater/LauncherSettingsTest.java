package org.beefmc.updater;

import org.junit.jupiter.api.Test;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

final class LauncherSettingsTest {
    @Test
    void automaticUpdatesDefaultToEnabled() throws Exception {
        assertTrue(LauncherSettings.load(Files.createTempDirectory("beefmc-settings-default")).isAutoUpdate());
    }

    @Test
    void automaticUpdatesCanBeDisabledPerServer() throws Exception {
        Path directory = Files.createTempDirectory("beefmc-settings-disabled");
        Files.write(directory.resolve("beefmc-updater.properties"), "auto-update=false\n".getBytes(StandardCharsets.UTF_8));

        assertFalse(LauncherSettings.load(directory).isAutoUpdate());
    }

    @Test
    void commandLineOverrideTakesPrecedence() throws Exception {
        Path directory = Files.createTempDirectory("beefmc-settings-override");
        Files.write(directory.resolve("beefmc-updater.properties"), "auto-update=true\n".getBytes(StandardCharsets.UTF_8));

        assertFalse(LauncherSettings.load(directory, Boolean.FALSE).isAutoUpdate());
    }

    @Test
    void invalidSettingIsRejected() throws Exception {
        Path directory = Files.createTempDirectory("beefmc-settings-invalid");
        Files.write(directory.resolve("beefmc-updater.properties"), "auto-update=sometimes\n".getBytes(StandardCharsets.UTF_8));

        assertThrows(java.io.IOException.class, () -> LauncherSettings.load(directory));
    }
}
