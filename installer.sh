#!/bin/sh
# PP Channel Sync installer/update script
# by Paweł Pawełek <aio-iptv@wp.pl>

set -u

REPO_RAW="https://raw.githubusercontent.com/OliOli2013/PPChannelSync-Plugin/main"
UPDATE_JSON="/tmp/ppchannelsync_update.json"
IPK_FILE="/tmp/enigma2-plugin-extensions-ppchannelsync_latest_all.ipk"

say() { echo "[PP Channel Sync] $*"; }
fetch() {
    URL="$1"
    OUT="$2"
    if command -v wget >/dev/null 2>&1; then
        wget -q -O "$OUT" "$URL"
        return $?
    fi
    if command -v curl >/dev/null 2>&1; then
        curl -L -s -o "$OUT" "$URL"
        return $?
    fi
    return 1
}

say "Pobieranie informacji o najnowszej wersji..."
if ! fetch "$REPO_RAW/update.json" "$UPDATE_JSON"; then
    say "Błąd: nie udało się pobrać update.json"
    exit 1
fi

IPK_URL=$(sed -n 's/.*"ipk_url"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$UPDATE_JSON" | head -n 1)
VERSION=$(sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$UPDATE_JSON" | head -n 1)

if [ -z "${IPK_URL:-}" ]; then
    say "Błąd: brak ipk_url w update.json"
    exit 1
fi

say "Najnowsza wersja: ${VERSION:-nieznana}"
say "Pobieranie paczki IPK..."
if ! fetch "$IPK_URL" "$IPK_FILE"; then
    say "Błąd: nie udało się pobrać IPK"
    exit 1
fi

if [ ! -s "$IPK_FILE" ]; then
    say "Błąd: pobrany plik IPK jest pusty"
    exit 1
fi

say "Instalacja..."
opkg install --force-reinstall "$IPK_FILE"
RET=$?
if [ "$RET" -ne 0 ]; then
    say "Błąd instalacji opkg: $RET"
    exit "$RET"
fi

say "Gotowe. Wykonaj restart GUI, aby załadować wtyczkę."
exit 0
