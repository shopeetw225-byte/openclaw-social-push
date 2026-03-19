#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <source-file> [name-prefix]" >&2
  exit 2
fi

SRC="$1"
PREFIX="${2:-social-push}"
UPLOAD_DIR="/tmp/openclaw/uploads"

if [[ ! -f "$SRC" ]]; then
  echo "source file not found: $SRC" >&2
  exit 1
fi

mkdir -p "$UPLOAD_DIR"
EXT="${SRC##*.}"
if [[ "$EXT" == "$SRC" ]]; then
  EXT="bin"
fi

STAMP="$(date +%s)"
BASENAME="${PREFIX}-${STAMP}.${EXT}"
DEST="$UPLOAD_DIR/$BASENAME"
cp -f "$SRC" "$DEST"
printf '%s\n' "$DEST"
