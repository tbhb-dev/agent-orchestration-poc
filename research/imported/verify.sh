#!/usr/bin/env bash
# Recompute the checksums in MANIFEST.tsv against the original folders and
# against the copies under research/imported/. Exits non-zero on any mismatch,
# missing file, or copied file that the manifest does not list.
#
# SOURCE_ROOT (default ~/Code/github.com/tbhb) holds the original folders. When
# it does not exist, only the copies are checked.
set -u
here="$(cd "$(dirname "$0")" && pwd)"
manifest="$here/MANIFEST.tsv"
source_root="${SOURCE_ROOT:-$HOME/Code/github.com/tbhb}"

check_sources=1
if [ ! -d "$source_root" ]; then
    echo "source root $source_root not found; checking copies only"
    check_sources=0
fi

fail=0
rows=0
sources_ok=0
copies_ok=0
while IFS=$'\t' read -r folder path sha size status dest; do
    [ "$folder" = "folder" ] && continue
    rows=$((rows + 1))
    if [ "$check_sources" = 1 ]; then
        src="$source_root/$folder/$path"
        if [ ! -f "$src" ]; then
            echo "MISSING source: $src"; fail=1
        else
            got="$(sha256sum "$src" | cut -d' ' -f1)"
            if [ "$got" != "$sha" ]; then echo "MISMATCH source: $src"; fail=1; else sources_ok=$((sources_ok + 1)); fi
        fi
    fi
    if [ "$status" = "copied" ]; then
        copy="$here/../../$dest"
        if [ ! -f "$copy" ]; then
            echo "MISSING copy: $dest"; fail=1
        else
            got="$(sha256sum "$copy" | cut -d' ' -f1)"
            if [ "$got" != "$sha" ]; then echo "MISMATCH copy: $dest"; fail=1; else copies_ok=$((copies_ok + 1)); fi
        fi
    fi
done < "$manifest"

# Every file under the imported folders must be a manifest row.
while IFS= read -r f; do
    rel="${f#"$here/"}"
    if ! awk -F'\t' -v want="research/imported/$rel" '$5 == "copied" && $6 == want { found = 1 } END { exit !found }' "$manifest"; then
        echo "UNLISTED copy: $rel"; fail=1
    fi
done < <(find "$here/agent-peering-tests" "$here/agent-session-tests" -type f)

echo "rows=$rows sources_ok=$sources_ok copies_ok=$copies_ok"
if [ "$fail" = 0 ]; then echo "OK"; else echo "FAILED"; fi
exit "$fail"
