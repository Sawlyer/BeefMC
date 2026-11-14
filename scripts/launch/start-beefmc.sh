#!/usr/bin/env sh
set -eu
if [ "$#" -lt 1 ]; then
    echo "Usage: BEEFMC_MINECRAFT_VERSION=1.21.11 sh start-beefmc.sh SERVER.jar [server arguments]" >&2
    exit 2
fi
if [ -z "${BEEFMC_MINECRAFT_VERSION:-}" ]; then
    echo "Set BEEFMC_MINECRAFT_VERSION to 1.8.8, 1.21.11, 26.1.2, or 26.3." >&2
    exit 2
fi
jar=$1
shift
if [ ! -f BeefMC-Launcher.jar ]; then
    echo "BeefMC-Launcher.jar is required for automatic updates. Place it beside the server JAR." >&2
    exit 2
fi
java=${JAVA:-java}
if [ "${BEEFMC_PROFILE:-}" = compact ]; then
    if ! "$java" -XX:+UseCompactObjectHeaders -version >/dev/null 2>&1; then
        echo "The compact profile requires a Java runtime with UseCompactObjectHeaders support. Use Java 25." >&2
        exit 2
    fi
    exec "$java" -jar BeefMC-Launcher.jar --minecraft-version "$BEEFMC_MINECRAFT_VERSION" --server-jar "$jar" -- "-Xms${BEEFMC_XMS:-512M}" "-Xmx${BEEFMC_XMX:-2944M}" -XX:+UseCompactObjectHeaders "$@"
fi
exec "$java" -jar BeefMC-Launcher.jar --minecraft-version "$BEEFMC_MINECRAFT_VERSION" --server-jar "$jar" -- "-Xms${BEEFMC_XMS:-512M}" "-Xmx${BEEFMC_XMX:-3G}" "$@"
