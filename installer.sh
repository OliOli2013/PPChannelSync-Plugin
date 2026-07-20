#!/bin/sh
set -u
BASE="https://raw.githubusercontent.com/OliOli2013/PPChannelSync-Plugin/main"
MANIFEST="/tmp/ppchannelsync_update.json"
IPK="/tmp/enigma2-plugin-extensions-ppchannelsync_latest_all.ipk"
STAMP="$(date +%s 2>/dev/null || echo 0)"

echo "PP Channel Sync - installer"
rm -f "$MANIFEST" "$IPK"

fetch_file() {
    SRC="$1"
    DST="$2"
    if command -v wget >/dev/null 2>&1; then
        wget -q --no-check-certificate -O "$DST" "$SRC" && return 0
    fi
    if command -v curl >/dev/null 2>&1; then
        curl -L -k -sS --max-time 90 -o "$DST" "$SRC" && return 0
    fi
    return 1
}

fetch_file "$BASE/update.json?ppcs=$STAMP" "$MANIFEST" || {
    echo "Nie udało się pobrać update.json."
    exit 1
}

URL="$(sed -n 's/.*"url"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$MANIFEST" | head -n 1)"
[ -n "$URL" ] || URL="$(sed -n 's/.*"ipk_url"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$MANIFEST" | head -n 1)"
SHA="$(sed -n 's/.*"sha256"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$MANIFEST" | head -n 1)"
VERSION="$(sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$MANIFEST" | head -n 1)"
[ -n "$VERSION" ] || VERSION="$(sed -n 's/.*"latest_version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$MANIFEST" | head -n 1)"

if [ -z "$URL" ]; then
    echo "Nie udało się odczytać adresu IPK."
    exit 1
fi

fetch_file "$URL?ppcs=$STAMP" "$IPK" || {
    echo "Nie udało się pobrać IPK."
    exit 1
}

if [ ! -s "$IPK" ]; then
    echo "Pobrana paczka IPK jest pusta."
    exit 1
fi

if [ -n "$SHA" ] && command -v sha256sum >/dev/null 2>&1; then
    ACTUAL="$(sha256sum "$IPK" | awk '{print $1}')"
    if [ "$ACTUAL" != "$SHA" ]; then
        echo "Błędna suma SHA256. Instalacja zatrzymana."
        rm -f "$IPK"
        exit 1
    fi
fi

PLUGIN_DIR="/usr/lib/enigma2/python/Plugins/Extensions/PPChannelSync"
rm -rf "$PLUGIN_DIR/__pycache__" 2>/dev/null || true
rm -f "$PLUGIN_DIR"/*.pyc "$PLUGIN_DIR"/*.pyo 2>/dev/null || true

if command -v opkg >/dev/null 2>&1; then
    opkg install --force-reinstall --force-overwrite "$IPK" || exit 1
elif command -v dpkg >/dev/null 2>&1; then
    dpkg -i "$IPK" || exit 1
else
    echo "Brak menedżera opkg/dpkg."
    exit 1
fi

rm -rf "$PLUGIN_DIR/__pycache__" 2>/dev/null || true
rm -f "$PLUGIN_DIR"/*.pyc "$PLUGIN_DIR"/*.pyo 2>/dev/null || true
sync 2>/dev/null || true
rm -f "$MANIFEST" "$IPK"
echo "Zainstalowano PP Channel Sync ${VERSION}. Wykonaj restart GUI."
exit 0
