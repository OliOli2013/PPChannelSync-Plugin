#!/bin/sh
set -eu

REPO_RAW="https://raw.githubusercontent.com/OliOli2013/PPChannelSync-Plugin/main"
MANIFEST_URL="$REPO_RAW/update.json"
TMP_MANIFEST="/tmp/ppchannelsync_update.json"
TMP_IPK="/tmp/ppchannelsync_update.ipk"

cleanup() {
    rm -f "$TMP_MANIFEST" "$TMP_MANIFEST.part" "$TMP_IPK" "$TMP_IPK.part" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

fetch() {
    url="$1"
    out="$2"
    if command -v wget >/dev/null 2>&1; then
        wget -q -T 60 -O "$out" "$url"
    elif command -v curl >/dev/null 2>&1; then
        curl -fL --connect-timeout 20 --max-time 60 -o "$out" "$url"
    else
        echo "Błąd: brak wget i curl." >&2
        exit 1
    fi
}

json_value() {
    key="$1"
    sed -n 's/.*"'"$key"'"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$TMP_MANIFEST" | head -n 1
}

fetch "$MANIFEST_URL" "$TMP_MANIFEST.part"
mv -f "$TMP_MANIFEST.part" "$TMP_MANIFEST"

VERSION="$(json_value version)"
IPK_URL="$(json_value ipk_url)"
SHA256="$(json_value sha256)"

[ -n "$VERSION" ] || { echo "Błąd: brak wersji w update.json." >&2; exit 1; }
[ -n "$IPK_URL" ] || { echo "Błąd: brak ipk_url w update.json." >&2; exit 1; }

printf 'PP Channel Sync %s — pobieranie paczki...\n' "$VERSION"
fetch "$IPK_URL" "$TMP_IPK.part"
mv -f "$TMP_IPK.part" "$TMP_IPK"

[ -s "$TMP_IPK" ] || { echo "Błąd: pobrana paczka jest pusta." >&2; exit 1; }

if [ -n "$SHA256" ]; then
    if command -v sha256sum >/dev/null 2>&1; then
        GOT="$(sha256sum "$TMP_IPK" | awk '{print $1}')"
    elif command -v openssl >/dev/null 2>&1; then
        GOT="$(openssl dgst -sha256 "$TMP_IPK" | awk '{print $NF}')"
    else
        GOT=""
        echo "Ostrzeżenie: brak narzędzia do kontroli SHA256." >&2
    fi
    if [ -n "$GOT" ] && [ "$GOT" != "$SHA256" ]; then
        echo "Błąd: suma SHA256 paczki jest niezgodna." >&2
        echo "Oczekiwano: $SHA256" >&2
        echo "Pobrano:    $GOT" >&2
        exit 1
    fi
fi

if command -v ar >/dev/null 2>&1; then
    MEMBERS="$(ar t "$TMP_IPK" 2>/dev/null || true)"
    echo "$MEMBERS" | grep -q '^debian-binary$' || { echo "Błąd: to nie jest poprawna paczka IPK." >&2; exit 1; }
    echo "$MEMBERS" | grep -q '^control.tar' || { echo "Błąd: brak control.tar w IPK." >&2; exit 1; }
    echo "$MEMBERS" | grep -q '^data.tar' || { echo "Błąd: brak data.tar w IPK." >&2; exit 1; }
fi

command -v opkg >/dev/null 2>&1 || { echo "Błąd: brak opkg." >&2; exit 1; }
opkg install --force-reinstall "$TMP_IPK"

echo ""
echo "PP Channel Sync $VERSION został zainstalowany."
echo "Wykonaj restart GUI Enigma2."
