#!/usr/bin/env bash

(
PS1="$"
basedir="$(cd "$1" && pwd -P)"
workdir="$basedir/base"
gitcmd="git -c commit.gpgsign=false"
applycmd="$gitcmd am --quiet --3way --ignore-whitespace"
# Windows detection to workaround ARG_MAX limitation
windows="$([[ "$OSTYPE" == "cygwin" || "$OSTYPE" == "msys" ]] && echo "true" || echo "false")"

function applyPatch {
    what=$1
    target=$2
    branch=$3
    patch_folder=$4

    cd "$basedir/$what"
    $gitcmd fetch >/dev/null
    $gitcmd branch -f upstream "$branch" >/dev/null

    cd "$basedir"
    if [ ! -d "$basedir/$target" ]; then
        $gitcmd clone "$what" "$target"
    fi
    cd "$basedir/$target"

    echo "Syncing BeefMC source tree..."
    $gitcmd remote rm origin > /dev/null 2>&1
    $gitcmd remote rm upstream > /dev/null 2>&1
    $gitcmd remote add upstream "$basedir/$what" >/dev/null 2>&1
    $gitcmd checkout master 2>/dev/null || $gitcmd checkout -b master
    $gitcmd fetch upstream >/dev/null 2>&1
    $gitcmd reset --hard upstream/upstream

    echo "  Applying BeefMC patch set..."

    statusfile=".git/patch-apply-failed"
    rm -f "$statusfile"
    git config commit.gpgsign false
    $gitcmd am --abort >/dev/null 2>&1

    # Special case Windows handling because of ARG_MAX constraint
    if [[ $windows == "true" ]]; then
        echo "  Using workaround for Windows ARG_MAX constraint"
        find "$basedir/$patch_folder/"*.patch -print0 | xargs -0 $applycmd
    else
        $applycmd "$basedir/$patch_folder/"*.patch
    fi

    if [ "$?" != "0" ]; then
        echo 1 > "$statusfile"
        echo "  Something did not apply cleanly to $target."
        echo "  Please review above details and finish the apply then"
        echo "  save the changes with rebuildPatches.sh"

        # On Windows, finishing the patch apply will only fix the latest patch
        # users will need to rebuild from that point and then re-run the patch
        # process to continue
        if [[ $windows == "true" ]]; then
            echo ""
            echo "  Because you're on Windows you'll need to finish the AM,"
            echo "  rebuild all patches, and then re-run the patch apply again."
            echo "  Consider using the scripts with Windows Subsystem for Linux."
        fi

        exit 1
    else
        rm -f "$statusfile"
        echo "  BeefMC patch set applied cleanly"
    fi
}

if [ "$2" == "--setup" ]; then
    echo "Preparing build dependencies..."

    # Move into Paper dir
    cd "$workdir/Paper"
    basedir=$(pwd)

    # Apply Spigot
    (
        applyPatch Bukkit Spigot-API HEAD Bukkit-Patches &&
        applyPatch CraftBukkit Spigot-Server patched CraftBukkit-Patches
    ) || (
        echo "Failed to prepare server dependencies"
        exit 1
    ) || exit 1

    # Apply Paper
    (
        applyPatch Spigot-API PaperSpigot-API HEAD Spigot-API-Patches &&
        applyPatch Spigot-Server PaperSpigot-Server HEAD Spigot-Server-Patches
    ) || (
        echo "Failed to prepare base source patches"
        exit 1
    ) || exit 1

    # Move out of Paper
    basedir="$1"
    cd "$basedir"

    echo "Importing mapped server sources"

    ./scripts/importmcdev.sh "$basedir" || exit 1
fi

if [ ! -d "base/Paper/PaperSpigot-Server" ]; then
    echo "Required source tree is missing. Run './beefmc setup' first."
    exit 1
else
    # Apply the upstream patch stack for BeefMC
    (
        applyPatch "base/Paper/PaperSpigot-API" BeefMC-API HEAD patches/api &&
        applyPatch "base/Paper/PaperSpigot-Server" BeefMC-Server HEAD patches/server
        cd "$basedir"
    ) || (
        echo "Failed to apply BeefMC patches"
        exit 1
    ) || exit 1
fi
) || exit 1
