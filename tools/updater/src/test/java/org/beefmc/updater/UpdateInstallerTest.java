package org.beefmc.updater;

import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.Optional;
import java.util.jar.Attributes;
import java.util.jar.JarEntry;
import java.util.jar.JarOutputStream;
import java.util.jar.Manifest;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

final class UpdateInstallerTest {
    private static final String JAR_NAME = "BeefMC-26.3-v1.2.3.jar";
    private HttpServer server;
    private byte[] newJar;
    private byte[] checksum;
    private int checksumRequests;
    private int jarRequests;

    @BeforeEach
    void startServer() throws Exception {
        newJar = validJar("new-server");
        checksum = checksumText(newJar, JAR_NAME);
        checksumRequests = 0;
        jarRequests = 0;
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/releases/latest", exchange -> respond(exchange, 200, releaseJson()));
        server.createContext("/assets/server.jar", exchange -> {
            jarRequests++;
            respond(exchange, 200, newJar);
        });
        server.createContext("/assets/server.jar.sha256", exchange -> {
            checksumRequests++;
            respond(exchange, 200, checksum);
        });
        server.start();
    }

    @AfterEach
    void stopServer() {
        server.stop(0);
    }

    @Test
    void installsChecksumVerifiedJarAndKeepsPreviousJarAsBackup() throws Exception {
        Path directory = Files.createTempDirectory("beefmc-update-install");
        Path current = directory.resolve("server.jar");
        byte[] previous = validJar("old-server");
        Files.write(current, previous);

        UpdateInstaller.UpdateResult result = installer().install(current, asset(), true);

        assertEquals(UpdateInstaller.Outcome.INSTALLED, result.getOutcome());
        assertArrayEquals(newJar, Files.readAllBytes(current));
        assertArrayEquals(previous, Files.readAllBytes(UpdateInstaller.backupPath(current)));
    }

    @Test
    void checksumMismatchLeavesInstalledJarUntouched() throws Exception {
        Path directory = Files.createTempDirectory("beefmc-update-checksum");
        Path current = directory.resolve("server.jar");
        byte[] previous = validJar("old-server");
        Files.write(current, previous);
        checksum = checksumText(validJar("different-bytes"), JAR_NAME);

        assertThrows(IOException.class, () -> installer().install(current, asset(), true));

        assertArrayEquals(previous, Files.readAllBytes(current));
        assertFalse(Files.exists(UpdateInstaller.backupPath(current)));
    }

    @Test
    void rejectsInvalidJarEvenWhenChecksumMatches() throws Exception {
        Path directory = Files.createTempDirectory("beefmc-update-invalid-jar");
        Path current = directory.resolve("server.jar");
        byte[] previous = validJar("old-server");
        Files.write(current, previous);
        newJar = "not a jar".getBytes(StandardCharsets.UTF_8);
        checksum = checksumText(newJar, JAR_NAME);

        assertThrows(IOException.class, () -> installer().install(current, asset(), true));

        assertArrayEquals(previous, Files.readAllBytes(current));
    }

    @Test
    void disabledAutoUpdateDoesNotDownloadOrReplaceJar() throws Exception {
        Path directory = Files.createTempDirectory("beefmc-update-disabled");
        Path current = directory.resolve("server.jar");
        byte[] previous = validJar("old-server");
        Files.write(current, previous);

        UpdateInstaller.UpdateResult result = installer().install(current, asset(), false);

        assertEquals(UpdateInstaller.Outcome.DISABLED, result.getOutcome());
        assertArrayEquals(previous, Files.readAllBytes(current));
        assertEquals(0, checksumRequests);
    }

    @Test
    void restoresPreviousJarWhenFinalMoveFails() throws Exception {
        Path directory = Files.createTempDirectory("beefmc-update-rollback");
        Path current = directory.resolve("server.jar");
        byte[] previous = validJar("old-server");
        Files.write(current, previous);
        UpdateInstaller.Mover failOnInstall = new UpdateInstaller.Mover() {
            private int moves;

            @Override
            public void move(Path source, Path target, boolean replace) throws IOException {
                moves++;
                if (moves == 2) {
                    throw new IOException("simulated target replacement failure");
                }
                UpdateInstaller.systemMove(source, target, replace);
            }
        };

        assertThrows(IOException.class, () -> new UpdateInstaller(2000, 2000, failOnInstall).install(current, asset(), true));

        assertArrayEquals(previous, Files.readAllBytes(current));
        assertFalse(Files.exists(UpdateInstaller.backupPath(current)));
    }

    @Test
    void firstInstallWorksWhenServerJarDoesNotExistYet() throws Exception {
        Path directory = Files.createTempDirectory("beefmc-update-first-install");
        Path current = directory.resolve("server.jar");

        UpdateInstaller.UpdateResult result = installer().install(current, asset(), true);

        assertEquals(UpdateInstaller.Outcome.INSTALLED, result.getOutcome());
        assertArrayEquals(newJar, Files.readAllBytes(current));
        assertFalse(Files.exists(UpdateInstaller.backupPath(current)));
    }

    @Test
    void alreadyCurrentJarIsNotReplacedOrBackedUp() throws Exception {
        Path directory = Files.createTempDirectory("beefmc-update-already-current");
        Path current = directory.resolve("server.jar");
        Files.write(current, newJar);

        UpdateInstaller.UpdateResult result = installer().install(current, asset(), true);

        assertEquals(UpdateInstaller.Outcome.ALREADY_CURRENT, result.getOutcome());
        assertArrayEquals(newJar, Files.readAllBytes(current));
        assertFalse(Files.exists(UpdateInstaller.backupPath(current)));
    }

    @Test
    void recoversPreviousJarWhenUpdateWasInterruptedAfterBackupMove() throws Exception {
        Path directory = Files.createTempDirectory("beefmc-update-recover-missing");
        Path current = directory.resolve("server.jar");
        byte[] previous = validJar("old-server");
        Files.write(UpdateInstaller.backupPath(current), previous);

        assertTrue(UpdateInstaller.recoverBackup(current));

        assertArrayEquals(previous, Files.readAllBytes(current));
        assertFalse(Files.exists(UpdateInstaller.backupPath(current)));
    }

    @Test
    void recoversPreviousJarWhenInterruptedReplacementLeftInvalidJar() throws Exception {
        Path directory = Files.createTempDirectory("beefmc-update-recover-invalid");
        Path current = directory.resolve("server.jar");
        byte[] previous = validJar("old-server");
        Files.write(current, "partial jar".getBytes(StandardCharsets.UTF_8));
        Files.write(UpdateInstaller.backupPath(current), previous);

        assertTrue(UpdateInstaller.recoverBackup(current));

        assertArrayEquals(previous, Files.readAllBytes(current));
        assertFalse(Files.exists(UpdateInstaller.backupPath(current)));
    }

    @Test
    void keepsValidCurrentJarAndBackupUntouchedDuringRecoveryCheck() throws Exception {
        Path directory = Files.createTempDirectory("beefmc-update-recover-current");
        Path current = directory.resolve("server.jar");
        Path backup = UpdateInstaller.backupPath(current);
        byte[] installed = validJar("current-server");
        Files.write(current, installed);
        Files.write(backup, validJar("previous-server"));

        assertFalse(UpdateInstaller.recoverBackup(current));

        assertArrayEquals(installed, Files.readAllBytes(current));
        assertTrue(Files.exists(backup));
    }

    @Test
    void skipsLargeDownloadOnLaterStartupWhenInstalledJarMatchesState() throws Exception {
        Path directory = Files.createTempDirectory("beefmc-update-state");
        Path current = directory.resolve("server.jar");

        installer().install(current, asset(), true);
        int downloadsAfterFirstInstall = jarRequests;
        UpdateInstaller.UpdateResult result = installer().install(current, asset(), true);

        assertEquals(UpdateInstaller.Outcome.ALREADY_CURRENT, result.getOutcome());
        assertEquals(downloadsAfterFirstInstall, jarRequests);
        assertTrue(Files.isRegularFile(UpdateInstaller.statePath(directory)));
        assertEquals("v1.2.3", UpdateInstaller.installedReleaseTag(current));
    }

    @Test
    void doesNotTrustSavedReleaseTagWhenInstalledJarHashChanged() throws Exception {
        Path directory = Files.createTempDirectory("beefmc-update-state-mismatch");
        Path current = directory.resolve("server.jar");
        installer().install(current, asset(), true);
        Files.write(current, validJar("manually replaced server"));

        assertEquals("", UpdateInstaller.installedReleaseTag(current));
    }

    private UpdateInstaller installer() {
        return new UpdateInstaller(2000, 2000);
    }

    private ReleaseClient.ReleaseAsset asset() throws Exception {
        URL endpoint = new URL("http://127.0.0.1:" + server.getAddress().getPort() + "/releases/latest");
        Optional<ReleaseClient.ReleaseAsset> result = new ReleaseClient(endpoint, 2000, 2000).latest("26.3");
        assertTrue(result.isPresent());
        return result.get();
    }

    private String releaseJson() {
        String base = "http://127.0.0.1:" + server.getAddress().getPort();
        return "{\"tag_name\":\"v1.2.3\",\"prerelease\":false,\"assets\":["
            + "{\"name\":\"" + JAR_NAME + "\",\"browser_download_url\":\"" + base + "/assets/server.jar\"},"
            + "{\"name\":\"" + JAR_NAME + ".sha256\",\"browser_download_url\":\"" + base + "/assets/server.jar.sha256\"}]}";
    }

    private static byte[] validJar(String value) throws IOException {
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        Manifest manifest = new Manifest();
        manifest.getMainAttributes().put(Attributes.Name.MANIFEST_VERSION, "1.0");
        try (JarOutputStream jar = new JarOutputStream(bytes, manifest)) {
            jar.putNextEntry(new JarEntry("server-version.txt"));
            jar.write(value.getBytes(StandardCharsets.UTF_8));
            jar.closeEntry();
        }
        return bytes.toByteArray();
    }

    private static byte[] checksumText(byte[] bytes, String name) throws Exception {
        byte[] digest = MessageDigest.getInstance("SHA-256").digest(bytes);
        StringBuilder hex = new StringBuilder();
        for (byte value : digest) {
            hex.append(String.format("%02x", value & 0xff));
        }
        return (hex + "  " + name + "\n").getBytes(StandardCharsets.US_ASCII);
    }

    private static void respond(com.sun.net.httpserver.HttpExchange exchange, int status, String body) throws IOException {
        respond(exchange, status, body.getBytes(StandardCharsets.UTF_8));
    }

    private static void respond(com.sun.net.httpserver.HttpExchange exchange, int status, byte[] body) throws IOException {
        exchange.sendResponseHeaders(status, body.length);
        try (OutputStream output = exchange.getResponseBody()) {
            output.write(body);
        }
    }
}
