#!/bin/sh
set -eu
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
VERSION="2.1.0"
BUILD="$ROOT/release/build"
CONTROL="$BUILD/control"
DATA="$BUILD/data"
OUT="$ROOT/packages/enigma2-plugin-extensions-ppchannelsync_${VERSION}_all.ipk"

rm -rf "$BUILD"
mkdir -p "$CONTROL" "$DATA/usr/lib/enigma2/python/Plugins/Extensions/PPChannelSync" "$ROOT/packages"
cp "$ROOT/usr/lib/enigma2/python/Plugins/Extensions/PPChannelSync/__init__.py" "$DATA/usr/lib/enigma2/python/Plugins/Extensions/PPChannelSync/"
cp "$ROOT/usr/lib/enigma2/python/Plugins/Extensions/PPChannelSync/plugin.py" "$DATA/usr/lib/enigma2/python/Plugins/Extensions/PPChannelSync/"
cp "$ROOT/usr/lib/enigma2/python/Plugins/Extensions/PPChannelSync/plugin.png" "$DATA/usr/lib/enigma2/python/Plugins/Extensions/PPChannelSync/"
cp "$ROOT/usr/lib/enigma2/python/Plugins/Extensions/PPChannelSync/qr.png" "$DATA/usr/lib/enigma2/python/Plugins/Extensions/PPChannelSync/"

cat > "$CONTROL/control" <<CONTROL
Package: enigma2-plugin-extensions-ppchannelsync
Version: $VERSION
Section: base
Priority: optional
Architecture: all
Maintainer: by Pawel Pawelek <aio-iptv@wp.pl>
Depends: enigma2
Description: PP Channel Sync $VERSION - multi-satellite correction, verified new channels at bouquet ends, lamedb4/lamedb5, backup and rollback, Python 2/3
CONTROL

cat > "$CONTROL/postinst" <<'POSTINST'
#!/bin/sh
PLUGIN_DIR="/usr/lib/enigma2/python/Plugins/Extensions/PPChannelSync"
rm -rf "$PLUGIN_DIR/__pycache__" 2>/dev/null || true
rm -f "$PLUGIN_DIR"/*.pyc "$PLUGIN_DIR"/*.pyo 2>/dev/null || true
exit 0
POSTINST
chmod 755 "$CONTROL/postinst"
printf '2.0\n' > "$BUILD/debian-binary"
(
  cd "$CONTROL"
  tar --owner=0 --group=0 -cJf "$BUILD/control.tar.xz" control postinst
)
(
  cd "$DATA"
  tar --owner=0 --group=0 -cJf "$BUILD/data.tar.xz" .
)
rm -f "$OUT"
(
  cd "$BUILD"
  ar r "$OUT" debian-binary control.tar.xz data.tar.xz >/dev/null
)
sha256sum "$OUT" | sed "s#  .*#  $(basename "$OUT")#" > "$OUT.sha256"
echo "$OUT"
