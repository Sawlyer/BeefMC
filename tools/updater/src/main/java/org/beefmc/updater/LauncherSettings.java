package org.beefmc.updater;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Properties;

public final class LauncherSettings {
    private final boolean autoUpdate;

    private LauncherSettings(boolean autoUpdate) {
        this.autoUpdate = autoUpdate;
    }

    static LauncherSettings disabled() {
        return new LauncherSettings(false);
    }

    public static LauncherSettings load(Path serverDirectory) throws IOException {
        return load(serverDirectory, null);
    }

    public static LauncherSettings load(Path serverDirectory, Boolean override) throws IOException {
        Path settingsFile = serverDirectory.resolve("beefmc-updater.properties");
        Properties properties = new Properties();
        if (Files.isRegularFile(settingsFile)) {
            try (InputStream input = Files.newInputStream(settingsFile)) {
                properties.load(input);
            }
        }
        String configured = override == null ? properties.getProperty("auto-update", "true").trim() : override.toString();
        if (!"true".equalsIgnoreCase(configured) && !"false".equalsIgnoreCase(configured)) {
            throw new IOException("auto-update must be true or false in " + settingsFile);
        }
        return new LauncherSettings(Boolean.parseBoolean(configured));
    }

    public boolean isAutoUpdate() {
        return autoUpdate;
    }
}
