# Automatic updates

BeefMC releases include one server JAR per supported Minecraft version, a SHA-256 file for each server JAR, and `BeefMC-Launcher.jar` with its own SHA-256 file. The launcher runs on Java 8 or later and is compatible with the legacy server runtime.

## Existing server setup

1. Download `BeefMC-Launcher.jar` and `BeefMC-Launcher.jar.sha256` from the same BeefMC release.
2. Verify the launcher checksum before installing it. On Windows, use `Get-FileHash BeefMC-Launcher.jar -Algorithm SHA256`; on Linux, use `sha256sum -c BeefMC-Launcher.jar.sha256`.
3. Place the launcher in each server directory, next to that server's current JAR.
4. Update the startup command to name the matching Minecraft version and existing JAR.

Windows:

```bat
set BEEFMC_MINECRAFT_VERSION=1.21.11
start-beefmc.cmd beefmc-paperclip.jar --nogui
```

Linux:

```sh
BEEFMC_MINECRAFT_VERSION=1.21.11 ./start-beefmc.sh beefmc-paperclip.jar --nogui
```

Use Minecraft version `1.8.8`, `1.21.11`, `26.1.2`, or `26.3`. Set version separately for each server service. The provided scripts keep the existing heap defaults and forward server arguments. Direct launcher command remains available:

```sh
java -jar BeefMC-Launcher.jar --minecraft-version 1.21.11 --server-jar beefmc-paperclip.jar -- -Xms512M -Xmx3G --nogui
```

The launcher starts the server as a child process, forwards its input/output, and returns its exit code.

## Behavior and recovery

Automatic updates are enabled when `beefmc-updater.properties` is missing. To opt out for one server, create this file in its working directory:

```properties
auto-update=false
```

At startup, the launcher queries the latest stable BeefMC GitHub release, picks the exact Minecraft artifact, downloads its checksum and JAR, validates SHA-256 and JAR format, then replaces the server JAR. The previous JAR remains as `<server-jar>.previous`. Failed lookup, download, checksum, or replacement leaves the old server JAR in place and starts it. If replacement began but failed, launcher attempts rollback before startup. If the process ends between moving the old and new JARs, next start restores the valid `.previous` JAR.

The running server is never restarted by the updater. `/ver` reports a cached release check; an available version installs at next launcher start. Direct server-JAR startup still works, but cannot auto-install releases. Each server folder needs its own launcher startup command.
