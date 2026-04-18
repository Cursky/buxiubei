#!/usr/bin/env bash
# moying-check-context.sh — Output harness context as JSON
#
# Usage: ./moying-check-context.sh [--json]
# Output: {"HARNESS_DIR":"...","PROJECT_DIR":"...","HAS_CLARIFICATIONS":true,...}

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/moying-common.sh"

JSON_MODE=false
for arg in "$@"; do
    case "$arg" in
        --json) JSON_MODE=true ;;
        --help|-h) echo "Usage: $0 [--json]"; exit 0 ;;
    esac
done

# Check initialization
if ! ensure_harness_initialized 2>/dev/null; then
    if $JSON_MODE; then
        echo '{"INITIALIZED":false,"ERROR":"项目未初始化，请先运行 /moying-init"}'
    else
        echo "ERROR: 项目未初始化。请先运行 /moying-init"
    fi
    exit 0  # exit 0 so callers can always parse the JSON; INITIALIZED=false signals the state
fi

HARNESS_DIR=$(get_harness_dir)
PROJECT_DIR=$(get_project_root)

# Check file existence and non-emptiness
has_content() {
    local file="$1"
    [ -f "$file" ] && [ -s "$file" ] && grep -q '[^[:space:]]' "$file" 2>/dev/null
}

# Count lines matching pattern in clarifications
clarification_count() {
    if [ -f "$HARNESS_DIR/clarifications.md" ]; then
        grep -c '^\- \[' "$HARNESS_DIR/clarifications.md" 2>/dev/null || echo "0"
    else
        echo "0"
    fi
}

# Count plans
plan_count() {
    local count=0
    if [ -d "$HARNESS_DIR/plans" ]; then
        for d in "$HARNESS_DIR/plans"/[0-9][0-9][0-9]-*/; do
            [ -d "$d" ] && count=$((count + 1))
        done
    fi
    echo "$count"
}

# Count designs
design_count() {
    local count=0
    if [ -d "$HARNESS_DIR/designs" ]; then
        for f in "$HARNESS_DIR/designs"/[0-9][0-9][0-9]-*.md; do
            [ -f "$f" ] && count=$((count + 1))
        done
    fi
    echo "$count"
}

HAS_CLARIFICATIONS=$(has_content "$HARNESS_DIR/clarifications.md" && echo "true" || echo "false")
HAS_CONSTITUTION=$(has_content "$HARNESS_DIR/constitution.md" && echo "true" || echo "false")
HAS_PROJECT_SPEC=$(has_content "$HARNESS_DIR/project-spec.md" && echo "true" || echo "false")
HAS_PIPELINE_STATUS=$([ -f "$PROJECT_DIR/pipeline-status.md" ] && echo "true" || echo "false")
PLAN_COUNT=$(plan_count)
DESIGN_COUNT=$(design_count)
CLARIFICATION_COUNT=$(clarification_count)

# Plugin info
HAS_PLUGINS=$(has_content "$HARNESS_DIR/plugins.md" && echo "true" || echo "false")
PLUGIN_COUNT=0
ACTIVE_PLUGINS=""
if [ -f "$HARNESS_DIR/plugins.md" ]; then
    PLUGIN_COUNT=$(grep -c '| active |' "$HARNESS_DIR/plugins.md" 2>/dev/null || echo "0")
    # Extract plugin names from markdown table rows containing "| active |"
    ACTIVE_PLUGINS=$(python3 -c "
import re, sys
try:
    with open('$HARNESS_DIR/plugins.md', encoding='utf-8') as f:
        names = [m.group(1).strip() for line in f
                 if '| active |' in line
                 for m in [re.match(r'\|\s*(\S+)\s*\|', line)] if m]
    print(','.join(names))
except Exception:
    pass
" 2>/dev/null)
fi

if $JSON_MODE; then
    printf '{"INITIALIZED":true,"HARNESS_DIR":"%s","PROJECT_DIR":"%s","HAS_CLARIFICATIONS":%s,"HAS_CONSTITUTION":%s,"HAS_PROJECT_SPEC":%s,"HAS_PIPELINE_STATUS":%s,"HAS_PLUGINS":%s,"CLARIFICATION_COUNT":%s,"PLAN_COUNT":%s,"DESIGN_COUNT":%s,"PLUGIN_COUNT":%s,"ACTIVE_PLUGINS":"%s"}\n' \
        "$(json_escape "$HARNESS_DIR")" \
        "$(json_escape "$PROJECT_DIR")" \
        "$HAS_CLARIFICATIONS" \
        "$HAS_CONSTITUTION" \
        "$HAS_PROJECT_SPEC" \
        "$HAS_PIPELINE_STATUS" \
        "$HAS_PLUGINS" \
        "$CLARIFICATION_COUNT" \
        "$PLAN_COUNT" \
        "$DESIGN_COUNT" \
        "$PLUGIN_COUNT" \
        "$(json_escape "$ACTIVE_PLUGINS")"
else
    echo "HARNESS_DIR: $HARNESS_DIR"
    echo "PROJECT_DIR: $PROJECT_DIR"
    echo "HAS_CLARIFICATIONS: $HAS_CLARIFICATIONS ($CLARIFICATION_COUNT entries)"
    echo "HAS_CONSTITUTION: $HAS_CONSTITUTION"
    echo "HAS_PROJECT_SPEC: $HAS_PROJECT_SPEC"
    echo "HAS_PIPELINE_STATUS: $HAS_PIPELINE_STATUS"
    echo "HAS_PLUGINS: $HAS_PLUGINS ($PLUGIN_COUNT active)"
    echo "ACTIVE_PLUGINS: $ACTIVE_PLUGINS"
    echo "PLAN_COUNT: $PLAN_COUNT"
    echo "DESIGN_COUNT: $DESIGN_COUNT"
fi
