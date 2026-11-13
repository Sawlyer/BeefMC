#!/usr/bin/env sh
set -eu
if [ "$#" -lt 1 ]; then
    echo "Usage: sh start-beefmc.sh SERVER.jar [server arguments]" >&2
    exit 2
fi
jar=$1
shift
exec "${JAVA:-java}" "-Xms${BEEFMC_XMS:-512M}" "-Xmx${BEEFMC_XMX:-3G}" -jar "$jar" "$@"
