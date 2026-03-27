#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

left_dir="workflows"
right_dir=".github/workflows"

if [[ ! -d "$left_dir" || ! -d "$right_dir" ]]; then
  echo "workflow-source-parity: expected directories '$left_dir' and '$right_dir' to exist"
  exit 1
fi

left_list="$(mktemp)"
right_list="$(mktemp)"
cleanup() {
  rm -f "$left_list" "$right_list"
}
trap cleanup EXIT

find "$left_dir" -type f -name '*.md' | sed "s|^$left_dir/||" | sort > "$left_list"
find "$right_dir" -type f -name '*.md' | sed "s|^$right_dir/||" | sort > "$right_list"

if ! diff -u "$left_list" "$right_list" > /dev/null; then
  echo "workflow-source-parity: source file set mismatch between '$left_dir' and '$right_dir'"
  diff -u "$left_list" "$right_list" || true
  exit 1
fi

while IFS= read -r rel; do
  [[ -z "$rel" ]] && continue
  left_file="$left_dir/$rel"
  right_file="$right_dir/$rel"

  if ! cmp -s "$left_file" "$right_file"; then
    echo "workflow-source-parity: source content mismatch for '$rel'"
    diff -u "$left_file" "$right_file" || true
    exit 1
  fi
done < "$left_list"

echo "workflow-source-parity: OK"
