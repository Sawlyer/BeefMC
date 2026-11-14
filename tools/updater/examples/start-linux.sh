#!/usr/bin/env sh
set -eu
if [ "$#" -lt 2 ]; then
    echo "Usage: ./start-linux.sh MINECRAFT_VERSION SERVER.jar [server arguments]" >&2
    exit 2
fi
version=$1
jar=$2
shift 2
exec "${JAVA:-java}" -jar BeefMC-Launcher.jar --minecraft-version "$version" --server-jar "$jar" -- "$@"
