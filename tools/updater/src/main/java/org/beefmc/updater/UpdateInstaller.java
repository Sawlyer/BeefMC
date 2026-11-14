package org.beefmc.updater;

import java.io.IOException;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.InetAddress;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Locale;
import java.util.Properties;
import java.util.jar.JarFile;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class UpdateInstaller {
    private static final int MAX_JAR_BYTES = 512 * 1024 * 1024;
    private static final Pattern CHECKSUM = Pattern.compile("^([0-9a-fA-F]{64})(?:\\s+\\*?(.+))?\\s*$");

    private final int connectTimeoutMillis;
    private final int readTimeoutMillis;
    private final Mover mover;

    public UpdateInstaller(int connectTimeoutMillis, int readTimeoutMillis) {
        this(connectTimeoutMillis, readTimeoutMillis, UpdateInstaller::systemMove);
    }

    UpdateInstaller(int connectTimeoutMillis, int readTimeoutMillis, Mover mover) {
        if (connectTimeoutMillis < 1 || readTimeoutMillis < 1) {
            throw new IllegalArgumentException("HTTP timeouts must be positive");
        }
        if (mover == null) {
            throw new IllegalArgumentException("File mover is required");
        }
        this.connectTimeoutMillis = connectTimeoutMillis;
        this.readTimeoutMillis = readTimeoutMillis;
        this.mover = mover;
    }

    public UpdateResult install(Path currentJar, ReleaseClient.ReleaseAsset release, boolean enabled) throws IOException {
        if (!enabled) {
            return new UpdateResult(Outcome.DISABLED, release.getTag());
        }
        if (currentJar == null || release == null) {
            throw new IllegalArgumentException("Current JAR and release are required");
        }

        Path absoluteJar = currentJar.toAbsolutePath().normalize();
        if (!secureUrl(release.getDownloadUrl()) || !secureUrl(release.getChecksumUrl())) {
            throw new IOException("Release downloads must use HTTPS");
        }
        Path directory = absoluteJar.getParent();
        if (directory == null) {
            throw new IOException("Server JAR has no parent directory");
        }
        Files.createDirectories(directory);

        Path stateFile = statePath(directory);
        InstallState installed = readState(stateFile);
        if (installed != null && Files.isRegularFile(absoluteJar)) {
            String currentHash = sha256(absoluteJar);
            if (currentHash.equalsIgnoreCase(installed.sha256)
                && ReleaseStatusComparator.compare(installed.tag, release.getTag()) >= 0) {
                return new UpdateResult(Outcome.ALREADY_CURRENT, installed.tag);
            }
        }

        Path stagedJar = Files.createTempFile(directory, absoluteJar.getFileName().toString(), ".download");
        Path stagedChecksum = Files.createTempFile(directory, absoluteJar.getFileName().toString(), ".sha256");
        try {
            download(release.getDownloadUrl(), stagedJar, MAX_JAR_BYTES, connectTimeoutMillis, readTimeoutMillis);
            download(release.getChecksumUrl(), stagedChecksum, 4096, connectTimeoutMillis, readTimeoutMillis);
            String expectedHash = readExpectedHash(stagedChecksum, release.getName());
            String actualHash = sha256(stagedJar);
            if (!expectedHash.equalsIgnoreCase(actualHash)) {
                throw new IOException("Release JAR SHA-256 does not match its checksum file");
            }
            validateJar(stagedJar);

            if (Files.isRegularFile(absoluteJar) && sha256(absoluteJar).equalsIgnoreCase(actualHash)) {
                tryWriteState(stateFile, release.getTag(), actualHash);
                return new UpdateResult(Outcome.ALREADY_CURRENT, release.getTag());
            }

            Path backup = backupPath(absoluteJar);
            boolean hadCurrent = Files.exists(absoluteJar);
            if (hadCurrent) {
                mover.move(absoluteJar, backup, true);
            }
            try {
                mover.move(stagedJar, absoluteJar, true);
            } catch (IOException installFailure) {
                if (hadCurrent && Files.exists(backup)) {
                    try {
                        mover.move(backup, absoluteJar, true);
                    } catch (IOException rollbackFailure) {
                        installFailure.addSuppressed(rollbackFailure);
                    }
                }
                throw installFailure;
            }
            tryWriteState(stateFile, release.getTag(), actualHash);
            return new UpdateResult(Outcome.INSTALLED, release.getTag());
        } finally {
            Files.deleteIfExists(stagedJar);
            Files.deleteIfExists(stagedChecksum);
        }
    }

    public static void validateDownloadedJar(Path jar) throws IOException {
        validateJar(jar);
    }

    public static boolean recoverBackup(Path currentJar) throws IOException {
        if (currentJar == null) {
            throw new IllegalArgumentException("Current JAR is required");
        }
        Path absoluteJar = currentJar.toAbsolutePath().normalize();
        Path backup = backupPath(absoluteJar);
        if (Files.isRegularFile(absoluteJar)) {
            try {
                validateJar(absoluteJar);
                return false;
            } catch (IOException invalidCurrentJar) {
                if (!Files.isRegularFile(backup)) {
                    throw invalidCurrentJar;
                }
            }
        } else if (!Files.isRegularFile(backup)) {
            return false;
        }

        validateJar(backup);
        systemMove(backup, absoluteJar, true);
        return true;
    }

    public static Path backupPath(Path currentJar) {
        return currentJar.resolveSibling(currentJar.getFileName().toString() + ".previous");
    }

    public static Path statePath(Path serverDirectory) {
        return serverDirectory.resolve("beefmc-updater.state");
    }

    public static String installedReleaseTag(Path currentJar) throws IOException {
        if (currentJar == null) {
            throw new IllegalArgumentException("Current JAR is required");
        }
        Path absoluteJar = currentJar.toAbsolutePath().normalize();
        InstallState installed = readState(statePath(absoluteJar.getParent()));
        if (installed == null || !Files.isRegularFile(absoluteJar)) {
            return "";
        }
        return sha256(absoluteJar).equalsIgnoreCase(installed.sha256) ? installed.tag : "";
    }

    static void systemMove(Path source, Path target, boolean replace) throws IOException {
        StandardCopyOption[] atomic = replace
            ? new StandardCopyOption[] { StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING }
            : new StandardCopyOption[] { StandardCopyOption.ATOMIC_MOVE };
        try {
            Files.move(source, target, atomic);
        } catch (AtomicMoveNotSupportedException exception) {
            if (replace) {
                Files.move(source, target, StandardCopyOption.REPLACE_EXISTING);
            } else {
                Files.move(source, target);
            }
        }
    }

    private static void download(URL url, Path destination, int maximumBytes, int connectTimeoutMillis, int readTimeoutMillis) throws IOException {
        URL current = url;
        for (int redirects = 0; redirects <= 5; redirects++) {
            if (!secureUrl(current)) {
                throw new IOException("Release download redirected to an insecure URL");
            }
            HttpURLConnection connection = (HttpURLConnection) current.openConnection();
            connection.setConnectTimeout(connectTimeoutMillis);
            connection.setReadTimeout(readTimeoutMillis);
            connection.setInstanceFollowRedirects(false);
            connection.setRequestMethod("GET");
            connection.setRequestProperty("User-Agent", "BeefMC-Updater/1.0");
            try {
                int status = connection.getResponseCode();
                if (status == HttpURLConnection.HTTP_MOVED_PERM || status == HttpURLConnection.HTTP_MOVED_TEMP
                    || status == HttpURLConnection.HTTP_SEE_OTHER || status == 307 || status == 308) {
                    String location = connection.getHeaderField("Location");
                    if (location == null || redirects == 5) {
                        throw new IOException("Release download exceeded its redirect limit");
                    }
                    current = new URL(current, location);
                    continue;
                }
                if (status != HttpURLConnection.HTTP_OK) {
                    throw new IOException("Release download returned HTTP " + status);
                }
                int contentLength = connection.getContentLength();
                if (contentLength > maximumBytes) {
                    throw new IOException("Release asset exceeds allowed size");
                }
                try (InputStream input = connection.getInputStream(); java.io.OutputStream output = Files.newOutputStream(destination)) {
                    byte[] buffer = new byte[16384];
                    int total = 0;
                    int read;
                    while ((read = input.read(buffer)) != -1) {
                        total += read;
                        if (total > maximumBytes) {
                            throw new IOException("Release asset exceeds allowed size");
                        }
                        output.write(buffer, 0, read);
                    }
                }
                return;
            } finally {
                connection.disconnect();
            }
        }
        throw new IOException("Release download exceeded its redirect limit");
    }

    private static boolean secureUrl(URL url) {
        if ("https".equalsIgnoreCase(url.getProtocol())) {
            return true;
        }
        if (!"http".equalsIgnoreCase(url.getProtocol())) {
            return false;
        }
        try {
            return InetAddress.getByName(url.getHost()).isLoopbackAddress();
        } catch (IOException exception) {
            return false;
        }
    }

    private static String readExpectedHash(Path checksumFile, String expectedName) throws IOException {
        byte[] bytes = Files.readAllBytes(checksumFile);
        String line = new String(bytes, StandardCharsets.US_ASCII).trim();
        Matcher matcher = CHECKSUM.matcher(line);
        if (!matcher.matches()) {
            throw new IOException("Release checksum file has an invalid format");
        }
        String fileName = matcher.group(2);
        if (fileName != null && !expectedName.equals(fileName)) {
            throw new IOException("Release checksum names a different JAR");
        }
        return matcher.group(1).toLowerCase(Locale.ROOT);
    }

    private static InstallState readState(Path stateFile) {
        if (!Files.isRegularFile(stateFile)) {
            return null;
        }
        Properties properties = new Properties();
        try (InputStream input = Files.newInputStream(stateFile)) {
            properties.load(input);
            String tag = properties.getProperty("release", "");
            String hash = properties.getProperty("sha256", "");
            if (!tag.matches("v(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)")
                || !hash.matches("[0-9a-fA-F]{64}")) {
                return null;
            }
            return new InstallState(tag, hash);
        } catch (IOException | RuntimeException ignored) {
            return null;
        }
    }

    private void tryWriteState(Path stateFile, String tag, String hash) {
        Path temporary = null;
        try {
            temporary = Files.createTempFile(stateFile.getParent(), "beefmc-updater-state", ".tmp");
            String state = "release=" + tag + "\nsha256=" + hash + "\n";
            Files.write(temporary, state.getBytes(StandardCharsets.US_ASCII));
            mover.move(temporary, stateFile, true);
        } catch (IOException exception) {
            System.err.println("BeefMC updater state could not be saved; release will be verified again next startup: " + exception.getMessage());
        } finally {
            try {
                if (temporary != null) {
                    Files.deleteIfExists(temporary);
                }
            } catch (IOException ignored) {
                // A leftover state temp file does not prevent server startup.
            }
        }
    }

    private static final class InstallState {
        private final String tag;
        private final String sha256;

        private InstallState(String tag, String sha256) {
            this.tag = tag;
            this.sha256 = sha256;
        }
    }

    private static final class ReleaseStatusComparator {
        private static int compare(String first, String second) {
            String[] left = first.substring(1).split("\\.");
            String[] right = second.substring(1).split("\\.");
            try {
                for (int index = 0; index < left.length; index++) {
                    int comparison = Integer.compare(Integer.parseInt(left[index]), Integer.parseInt(right[index]));
                    if (comparison != 0) {
                        return comparison;
                    }
                }
                return 0;
            } catch (RuntimeException invalidTag) {
                return first.compareTo(second);
            }
        }
    }

    private static String sha256(Path file) throws IOException {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            try (InputStream input = Files.newInputStream(file)) {
                byte[] buffer = new byte[16384];
                int read;
                while ((read = input.read(buffer)) != -1) {
                    digest.update(buffer, 0, read);
                }
            }
            StringBuilder hex = new StringBuilder(64);
            for (byte value : digest.digest()) {
                hex.append(String.format(Locale.ROOT, "%02x", value & 0xff));
            }
            return hex.toString();
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException("SHA-256 is unavailable", exception);
        }
    }

    private static void validateJar(Path file) throws IOException {
        try (JarFile jar = new JarFile(file.toFile(), true)) {
            if (jar.getManifest() == null) {
                throw new IOException("Downloaded file is not a BeefMC server JAR");
            }
        } catch (RuntimeException exception) {
            throw new IOException("Downloaded file is not a valid JAR", exception);
        }
    }

    interface Mover {
        void move(Path source, Path target, boolean replace) throws IOException;
    }

    public enum Outcome {
        DISABLED,
        ALREADY_CURRENT,
        INSTALLED
    }

    public static final class UpdateResult {
        private final Outcome outcome;
        private final String releaseTag;

        private UpdateResult(Outcome outcome, String releaseTag) {
            this.outcome = outcome;
            this.releaseTag = releaseTag;
        }

        public Outcome getOutcome() {
            return outcome;
        }

        public String getReleaseTag() {
            return releaseTag;
        }
    }
}
