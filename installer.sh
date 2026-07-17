#!/bin/sh
set -u
BASE="https://raw.githubusercontent.com/OliOli2013/PPChannelSync-Plugin/main"
MANIFEST="/tmp/ppchannelsync_update.json"
IPK="/tmp/enigma2-plugin-extensions-ppchannelsync_latest_all.ipk"

echo "PP Channel Sync - installer"
rm -f "$MANIFEST" "$IPK"

if command -v wget >/dev/null 2>&1; then
    wget -q --no-check-certificate -O "$MANIFEST" "$BASE/update.json" || exit 1
elif command -v curl >/dev/null 2>&1; then
    curl -L -k -sS -o "$MANIFEST" "$BASE/update.json" || exit 1
else
    echo "Brak wget i curl."
    exit 1
fi

URL="$(sed -n 's/.*"url"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$MANIFEST" | head -n 1)"
SHA="$(sed -n 's/.*"sha256"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$MANIFEST" | head -n 1)"
VERSION="$(sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$MANIFEST" | head -n 1)"

if [ -z "$URL" ]; then
    echo "Nie udało się odczytać adresu IPK."
    exit 1
fi

if command -v wget >/dev/null 2>&1; then
    wget -q --no-check-certificate -O "$IPK" "$URL" || exit 1
else
    curl -L -k -sS -o "$IPK" "$URL" || exit 1
fi

if [ -n "$SHA" ] && command -v sha256sum >/dev/null 2>&1; then
    ACTUAL="$(sha256sum "$IPK" | awk '{print $1}')"
    if [ "$ACTUAL" != "$SHA" ]; then
        echo "Błędna suma SHA256. Instalacja zatrzymana."
        rm -f "$IPK"
        exit 1
    fi
fi

if command -v opkg >/dev/null 2>&1; then
    opkg install --force-reinstall "$IPK" || exit 1
elif command -v dpkg >/dev/null 2>&1; then
    dpkg -i "$IPK" || exit 1
else
    echo "Brak menedżera opkg/dpkg."
    exit 1
fi

rm -f "$MANIFEST" "$IPK"
echo "Zainstalowano PP Channel Sync ${VERSION}. Wykonaj restart GUI."
exit 0
