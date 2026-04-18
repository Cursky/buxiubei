#!/usr/bin/env bash
# moying-common.sh — Shared functions for moying harness commands
# Source this file: source "$(dirname "$0")/moying-common.sh"
#
# Modeled after .specify/scripts/bash/common.sh

# Find .harness/ directory by searching upward from given dir
find_harness_root() {
    local dir="${1:-$(pwd)}"
    dir="$(cd -- "$dir" 2>/dev/null && pwd)" || return 1
    local prev_dir=""
    while true; do
        if [ -d "$dir/.harness" ]; then
            echo "$dir"
            return 0
        fi
        if [ "$dir" = "/" ] || [ "$dir" = "$prev_dir" ]; then
            break
        fi
        prev_dir="$dir"
        dir="$(dirname "$dir")"
    done
    return 1
}

# Get .harness/ directory path, or fail
get_harness_dir() {
    local root
    if root=$(find_harness_root); then
        echo "$root/.harness"
        return 0
    fi
    echo "ERROR: .harness/ 目录未找到。请先运行 /moying-init" >&2
    return 1
}

# Get project root (parent of .harness/)
get_project_root() {
    find_harness_root || return 1
}

# Check if harness is initialized
ensure_harness_initialized() {
    if ! find_harness_root > /dev/null 2>&1; then
        echo "ERROR: 项目未初始化。请先运行 /moying-init" >&2
        return 1
    fi
    return 0
}

# Get next plan number by scanning .harness/plans/
get_next_plan_number() {
    local harness_dir
    harness_dir=$(get_harness_dir) || return 1
    local plans_dir="$harness_dir/plans"
    local max_num=0

    if [ -d "$plans_dir" ]; then
        for d in "$plans_dir"/[0-9][0-9][0-9]-*/; do
            [ -d "$d" ] || continue
            local name=$(basename "$d")
            local num=${name%%-*}
            num=$((10#$num))  # strip leading zeros
            if [ "$num" -gt "$max_num" ]; then
                max_num=$num
            fi
        done
    fi

    printf "%03d\n" $((max_num + 1))
}

# Get next design number by scanning .harness/designs/
get_next_design_number() {
    local harness_dir
    harness_dir=$(get_harness_dir) || return 1
    local designs_dir="$harness_dir/designs"
    local max_num=0

    if [ -d "$designs_dir" ]; then
        for f in "$designs_dir"/[0-9][0-9][0-9]-*.md; do
            [ -f "$f" ] || continue
            local name=$(basename "$f" .md)
            local num=${name%%-*}
            num=$((10#$num))
            if [ "$num" -gt "$max_num" ]; then
                max_num=$num
            fi
        done
    fi

    printf "%03d\n" $((max_num + 1))
}

# Slugify a topic string for use in filenames (portable — no sed Unicode)
slugify() {
    # Use Python for reliable Unicode handling
    python3 -c "
import re, sys
s = sys.argv[1].lower()
s = re.sub(r'[^\w\u4e00-\u9fff]', '-', s)
s = re.sub(r'-+', '-', s).strip('-')[:50]
print(s)
" "$1" 2>/dev/null || echo "$1" | tr ' ' '-' | cut -c1-50
}

# Simple JSON escape (no jq dependency)
json_escape() {
    local str="$1"
    str="${str//\\/\\\\}"
    str="${str//\"/\\\"}"
    str="${str//$'\n'/\\n}"
    echo "$str"
}

# Check if jq is available
has_jq() {
    command -v jq > /dev/null 2>&1
}
