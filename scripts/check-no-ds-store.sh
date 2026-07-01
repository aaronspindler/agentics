#!/usr/bin/env bash
set -euo pipefail

found="$(find . -path ./.git -prune -o -name .DS_Store -type f -print)"

if [[ -n "$found" ]]; then
  printf '%s\n' \
    "Found macOS Finder metadata files:" \
    "$found" \
    "" \
    "Remove them before committing, for example:" \
    "  find . -path ./.git -prune -o -name .DS_Store -type f -delete"
  exit 1
fi
