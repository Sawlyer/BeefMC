#!/usr/bin/env sh
set -eu
if [ "$#" -lt 1 ]; then
    echo "Usage: sh start-beefmc.sh SERVER.jar [server arguments]" >&2
    exit 2
fi
jar=$1
shift
java=${JAVA:-java}
if [ "${BEEFMC_PROFILE:-}" = compact ]; then
    if ! "$java" -XX:+UseCompactObjectHeaders -version >/dev/null 2>&1; then
        echo "The compact profile requires a Java runtime with UseCompactObjectHeaders support. Use Java 25." >&2
        exit 2
    fi
    exec "$java" "-Xms${BEEFMC_XMS:-512M}" "-Xmx${BEEFMC_XMX:-2944M}" -XX:+UseCompactObjectHeaders -jar "$jar" "$@"
fi
exec "$java" "-Xms${BEEFMC_XMS:-512M}" "-Xmx${BEEFMC_XMX:-3G}" -jar "$jar" "$@"
