#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <staged-file> [staged-file ...]" >&2
  exit 2
fi

UPLOAD_DIR="/tmp/openclaw/uploads"

for PATH_ARG in "$@"; do
  case "$PATH_ARG" in
    "$UPLOAD_DIR"/*)
      if [[ -e "$PATH_ARG" ]]; then
        rm -f "$PATH_ARG"
      fi
      printf '%s\n' "$PATH_ARG"
      ;;
    *)
      echo "refusing to delete non-staged path: $PATH_ARG" >&2
      exit 1
      ;;
  esac
done
