package org.beefmc.updater;

import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

final class ReleaseClientTest {
    private HttpServer server;
    private int responseCode;
    private String responseBody;
    private boolean delayResponse;

    @BeforeEach
    void startServer() throws IOException {
        responseCode = 200;
        responseBody = "{}";
        delayResponse = false;
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/releases/latest", exchange -> {
            if (delayResponse) {
                try {
                    Thread.sleep(250L);
                } catch (InterruptedException exception) {
                    Thread.currentThread().interrupt();
                }
            }
            byte[] body = responseBody.getBytes(StandardCharsets.UTF_8);
            exchange.sendResponseHeaders(responseCode, body.length);
            try (OutputStream output = exchange.getResponseBody()) {
                output.write(body);
            }
        });
        server.start();
    }

    @AfterEach
    void stopServer() {
        server.stop(0);
    }

    @Test
    void assetNameMatchesReleaseCatalogForEachSupportedMinecraftVersion() {
        assertEquals("BeefMC-1.8.8-v1.2.3.jar", ReleaseClient.assetNameFor("1.8.8", "v1.2.3"));
        assertEquals("BeefMC-1.21.11-v1.2.3.jar", ReleaseClient.assetNameFor("1.21.11", "v1.2.3"));
        assertEquals("BeefMC-26.1.2-v1.2.3.jar", ReleaseClient.assetNameFor("26.1.2", "v1.2.3"));
        assertEquals("BeefMC-26.3-v1.2.3.jar", ReleaseClient.assetNameFor("26.3", "v1.2.3"));
    }

    @Test
    void rejectsMinecraftVersionOutsideActiveCatalog() {
        assertThrows(IllegalArgumentException.class, () -> ReleaseClient.assetNameFor("26.2", "v1.2.3"));
    }

    @Test
    void rejectsNonLoopbackHttpAssetUrl() throws Exception {
        responseBody = "{\"tag_name\":\"v1.2.3\",\"prerelease\":false,\"assets\":["
            + "{\"name\":\"BeefMC-26.3-v1.2.3.jar\",\"browser_download_url\":\"http://example.com/server.jar\"},"
            + "{\"name\":\"BeefMC-26.3-v1.2.3.jar.sha256\",\"browser_download_url\":\"https://example.com/server.jar.sha256\"}]}";

        assertThrows(IOException.class, () -> client(2000, 2000).latest("26.3"));
    }

    @Test
    void findsMatchingStableReleaseJarAndChecksum() throws Exception {
        responseBody = release("v1.2.3", false, "BeefMC-26.3-v1.2.3.jar");

        Optional<ReleaseClient.ReleaseAsset> result = client(2000, 2000).latest("26.3");

        assertTrue(result.isPresent());
        assertEquals("v1.2.3", result.get().getTag());
        assertEquals("BeefMC-26.3-v1.2.3.jar", result.get().getName());
        assertEquals("http://127.0.0.1:" + server.getAddress().getPort() + "/server.jar", result.get().getDownloadUrl().toString());
        assertEquals("http://127.0.0.1:" + server.getAddress().getPort() + "/server.jar.sha256", result.get().getChecksumUrl().toString());
    }

    @Test
    void ignoresPrereleaseEvenWhenAssetNamesMatch() throws Exception {
        responseBody = release("v1.2.3-rc1", true, "BeefMC-26.3-v1.2.3.jar");

        assertFalse(client(2000, 2000).latest("26.3").isPresent());
    }

    @Test
    void ignoresReleaseWithoutExactVersionAsset() throws Exception {
        responseBody = release("v1.2.3", false, "BeefMC-26.1.2-v1.2.3.jar");

        assertFalse(client(2000, 2000).latest("26.3").isPresent());
    }

    @Test
    void reportsHttpFailure() {
        responseCode = 503;
        responseBody = "unavailable";

        assertThrows(IOException.class, () -> client(2000, 2000).latest("26.3"));
    }

    @Test
    void reportsMalformedReleaseJson() {
        responseBody = "{";

        assertThrows(IOException.class, () -> client(2000, 2000).latest("26.3"));
    }

    @Test
    void readTimeoutBoundsReleaseLookup() {
        delayResponse = true;
        responseBody = release("v1.2.3", false, "BeefMC-26.3-v1.2.3.jar");

        assertThrows(IOException.class, () -> client(2000, 20).latest("26.3"));
    }

    private ReleaseClient client(int connectTimeout, int readTimeout) throws Exception {
        URL endpoint = new URL("http://127.0.0.1:" + server.getAddress().getPort() + "/releases/latest");
        return new ReleaseClient(endpoint, connectTimeout, readTimeout);
    }

    private String release(String tag, boolean prerelease, String jarName) {
        String base = "http://127.0.0.1:" + server.getAddress().getPort();
        return "{\"tag_name\":\"" + tag + "\",\"prerelease\":" + prerelease + ",\"assets\":["
            + "{\"name\":\"" + jarName + "\",\"browser_download_url\":\"" + base + "/server.jar\"},"
            + "{\"name\":\"" + jarName + ".sha256\",\"browser_download_url\":\"" + base + "/server.jar.sha256\"}]}";
    }
}
