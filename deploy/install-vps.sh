#!/usr/bin/env bash
# INSTALLER_ASSEMBLED_FROM_PARTS
set -Eeuo pipefail
dir="$(cd "$(dirname "$0")" && pwd)/install-vps-src"
tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT
for part in "$dir"/part-*; do
  base64 -d "$part" >> "$tmp"
done
exec bash "$tmp" "$@"
