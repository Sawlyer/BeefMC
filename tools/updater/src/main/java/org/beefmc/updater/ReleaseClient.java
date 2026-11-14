package org.beefmc.updater;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import java.io.IOException;
import java.io.InputStreamReader;
import java.io.Reader;
import java.net.HttpURLConnection;
import java.net.InetAddress;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.Optional;
import java.util.Set;
import java.util.regex.Pattern;

public final class ReleaseClient {
    private static final Set<String> SUPPORTED_VERSIONS = Collections.unmodifiableSet(new HashSet<String>(Arrays.asList(
        "1.8.8", "1.21.11", "26.1.2", "26.3"
    )));
    private static final Pattern STABLE_TAG = Pattern.compile("v(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)");
    private static final String DEFAULT_RELEASE_URL = "https://api.github.com/repos/Sawlyer/BeefMC/releases/latest";

    private final URL latestReleaseUrl;
    private final int connectTimeoutMillis;
    private final int readTimeoutMillis;

    public ReleaseClient() {
        this(toUrl(DEFAULT_RELEASE_URL), 5000, 10000);
    }

    public ReleaseClient(URL latestReleaseUrl, int connectTimeoutMillis, int readTimeoutMillis) {
        if (latestReleaseUrl == null) {
            throw new IllegalArgumentException("Release URL is required");
        }
        if (connectTimeoutMillis < 1 || readTimeoutMillis < 1) {
            throw new IllegalArgumentException("HTTP timeouts must be positive");
        }
        this.latestReleaseUrl = latestReleaseUrl;
        this.connectTimeoutMillis = connectTimeoutMillis;
        this.readTimeoutMillis = readTimeoutMillis;
    }

    public Optional<ReleaseAsset> latest(String minecraftVersion) throws IOException {
        if (!SUPPORTED_VERSIONS.contains(minecraftVersion)) {
            throw new IllegalArgumentException("Unsupported Minecraft version: " + minecraftVersion);
        }

        HttpURLConnection connection = (HttpURLConnection) latestReleaseUrl.openConnection();
        connection.setConnectTimeout(connectTimeoutMillis);
        connection.setReadTimeout(readTimeoutMillis);
        connection.setRequestMethod("GET");
        connection.setRequestProperty("Accept", "application/vnd.github+json");
        connection.setRequestProperty("User-Agent", "BeefMC-Updater/1.0");
        try {
            int status = connection.getResponseCode();
            if (status != HttpURLConnection.HTTP_OK) {
                throw new IOException("GitHub Releases returned HTTP " + status);
            }

            try (Reader reader = new InputStreamReader(connection.getInputStream(), StandardCharsets.UTF_8)) {
                JsonElement parsed = JsonParser.parseReader(reader);
                if (!parsed.isJsonObject()) {
                    throw new IOException("GitHub Releases response is not a JSON object");
                }
                JsonObject release = parsed.getAsJsonObject();
                String tag = requiredString(release, "tag_name");
                JsonElement prerelease = release.get("prerelease");
                if (prerelease == null || !prerelease.isJsonPrimitive() || !prerelease.getAsJsonPrimitive().isBoolean()) {
                    throw new IOException("GitHub Releases response has no prerelease flag");
                }
                JsonElement draft = release.get("draft");
                if (draft != null && (!draft.isJsonPrimitive() || !draft.getAsJsonPrimitive().isBoolean())) {
                    throw new IOException("GitHub Releases response has an invalid draft flag");
                }
                if ((draft != null && draft.getAsBoolean()) || prerelease.getAsBoolean() || !STABLE_TAG.matcher(tag).matches()) {
                    return Optional.empty();
                }

                String expectedName = assetNameFor(minecraftVersion, tag);
                JsonElement assetsElement = release.get("assets");
                if (assetsElement == null || !assetsElement.isJsonArray()) {
                    throw new IOException("GitHub Releases response has no assets list");
                }

                URL jarUrl = null;
                URL checksumUrl = null;
                JsonArray assets = assetsElement.getAsJsonArray();
                for (JsonElement element : assets) {
                    if (!element.isJsonObject()) {
                        continue;
                    }
                    JsonObject asset = element.getAsJsonObject();
                    String name = requiredString(asset, "name");
                    if (name.equals(expectedName) && jarUrl == null) {
                        jarUrl = assetUrl(asset);
                    } else if (name.equals(expectedName + ".sha256") && checksumUrl == null) {
                        checksumUrl = assetUrl(asset);
                    }
                }
                if (jarUrl == null || checksumUrl == null) {
                    return Optional.empty();
                }
                return Optional.of(new ReleaseAsset(tag, expectedName, jarUrl, checksumUrl));
            } catch (RuntimeException exception) {
                throw new IOException("Invalid GitHub Releases response", exception);
            }
        } finally {
            connection.disconnect();
        }
    }

    public static String assetNameFor(String minecraftVersion, String tag) {
        if (!SUPPORTED_VERSIONS.contains(minecraftVersion)) {
            throw new IllegalArgumentException("Unsupported Minecraft version: " + minecraftVersion);
        }
        if (tag == null || !STABLE_TAG.matcher(tag).matches()) {
            throw new IllegalArgumentException("Expected a stable vMAJOR.MINOR.PATCH release tag");
        }
        return "BeefMC-" + minecraftVersion + "-" + tag + ".jar";
    }

    public static boolean supports(String minecraftVersion) {
        return SUPPORTED_VERSIONS.contains(minecraftVersion);
    }

    private static URL assetUrl(JsonObject asset) throws IOException {
        String value = requiredString(asset, "browser_download_url");
        URL url;
        try {
            url = new URL(value);
        } catch (IOException exception) {
            throw new IOException("Invalid release asset URL", exception);
        }
        if (!"https".equalsIgnoreCase(url.getProtocol()) && !isLoopbackHttp(url)) {
            throw new IOException("Release asset URL must use HTTPS");
        }
        return url;
    }

    private static boolean isLoopbackHttp(URL url) {
        if (!"http".equalsIgnoreCase(url.getProtocol())) {
            return false;
        }
        try {
            return InetAddress.getByName(url.getHost()).isLoopbackAddress();
        } catch (IOException exception) {
            return false;
        }
    }

    private static String requiredString(JsonObject object, String key) throws IOException {
        JsonElement value = object.get(key);
        if (value == null || !value.isJsonPrimitive() || !value.getAsJsonPrimitive().isString()) {
            throw new IOException("GitHub Releases response is missing string field " + key);
        }
        return value.getAsString();
    }

    private static URL toUrl(String value) {
        try {
            return new URL(value);
        } catch (IOException exception) {
            throw new IllegalStateException(exception);
        }
    }

    public static final class ReleaseAsset {
        private final String tag;
        private final String name;
        private final URL downloadUrl;
        private final URL checksumUrl;

        private ReleaseAsset(String tag, String name, URL downloadUrl, URL checksumUrl) {
            this.tag = tag;
            this.name = name;
            this.downloadUrl = downloadUrl;
            this.checksumUrl = checksumUrl;
        }

        public String getTag() {
            return tag;
        }

        public String getName() {
            return name;
        }

        public URL getDownloadUrl() {
            return downloadUrl;
        }

        public URL getChecksumUrl() {
            return checksumUrl;
        }
    }
}
