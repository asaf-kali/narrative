#!/usr/bin/env bash
# Fetch encrypted WhatsApp DBs from connected Android device via adb.
# Usage: fetch_db.sh [dest_dir]
# Env: ADB (default: adb.exe), WA_REMOTE_DIR (default: WhatsApp Databases path)
set -euo pipefail

DEST="${1:-data}"
WA_BASE_DIR="${WA_BASE_DIR:-/sdcard/Android/media/com.whatsapp/WhatsApp}"

find_adb() {
    if [[ -n "${ADB:-}" ]]; then echo "$ADB"; return; fi
    if command -v adb.exe >/dev/null 2>&1; then echo "adb.exe"; return; fi
    if command -v adb >/dev/null 2>&1; then echo "adb"; return; fi
    local winget_glob="/mnt/c/Users/*/AppData/Local/Microsoft/WinGet/Packages/Google.PlatformTools_*/platform-tools/adb.exe"
    local found
    found=$(compgen -G "$winget_glob" 2>/dev/null | head -1 || true)
    if [[ -n "$found" ]]; then echo "$found"; return; fi
    echo ""
}

ADB=$(find_adb)
if [[ -z "$ADB" ]] || ! command -v "$ADB" >/dev/null 2>&1; then
    echo "adb not found. Install Windows platform-tools (winget install Google.PlatformTools), add to Windows PATH, or set ADB=/path/to/adb.exe" >&2
    exit 1
fi
echo "Using adb: $ADB"

if ! "$ADB" get-state 2>&1 | grep -q "device"; then
    echo "No authorized device. Run '$ADB devices' — enable USB debugging + tap Allow on phone." >&2
    exit 1
fi

mkdir -p "$DEST"
"$ADB" pull "$WA_BASE_DIR/Databases/msgstore.db.crypt15" "$DEST/"
"$ADB" pull "$WA_BASE_DIR/Backups/wa.db.crypt15" "$DEST/" || echo "wa.db.crypt15 not present, skipping"
echo "Pulled to $DEST/"
