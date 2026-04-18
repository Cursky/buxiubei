#!/usr/bin/env bash
# moying-load-plugins.sh — Plugin knowledge loader (fine-grained)
#
# Usage:
#   moying-load-plugins.sh --list-available    # List globally available plugins (JSON)
#   moying-load-plugins.sh --list-enabled      # List project-enabled plugins (JSON)
#   moying-load-plugins.sh --load-knowledge    # Load active plugins' knowledge (JSON)
#   moying-load-plugins.sh --load-meta         # Load active plugins' metadata only (JSON)
#
# All output is JSON. Called by SKILL.md files for fine-grained plugin loading.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." 2>/dev/null && pwd)"

# Locate harness module — check project dir first, then ~/.moying/
if [ -f "$PROJECT_DIR/harness/plugins.py" ]; then
    HARNESS_PARENT="$PROJECT_DIR"
elif [ -f "$HOME/.moying/harness/plugins.py" ]; then
    HARNESS_PARENT="$HOME/.moying"
else
    echo '{"error":"harness/plugins.py not found"}' >&2
    exit 1
fi

run_plugin_cmd() {
    local func="$1"
    cd "$PROJECT_DIR"
    PYTHONPATH="$HARNESS_PARENT" python3 -c "
from harness.plugins import ${func}
print(${func}())
"
}

case "${1:-}" in
    --list-available)
        run_plugin_cmd "_cli_list_available"
        ;;
    --list-enabled)
        run_plugin_cmd "_cli_list_enabled"
        ;;
    --load-knowledge)
        if [ "${2:-}" = "--type" ] && [ -n "${3:-}" ]; then
            MOYING_PLUGIN_TYPE="$3" run_plugin_cmd "_cli_load_knowledge"
        else
            run_plugin_cmd "_cli_load_knowledge"
        fi
        ;;
    --load-meta)
        if [ "${2:-}" = "--type" ] && [ -n "${3:-}" ]; then
            MOYING_PLUGIN_TYPE="$3" run_plugin_cmd "_cli_load_meta"
        else
            run_plugin_cmd "_cli_load_meta"
        fi
        ;;
    --help|-h)
        echo "Usage: $0 [--list-available|--list-enabled|--load-knowledge [--type TYPE]|--load-meta [--type TYPE]]"
        echo "  --type TYPE  Filter by plugin type (e.g., optimization, workflow)"
        exit 0
        ;;
    *)
        echo "Error: unknown option '$1'. Use --help for usage." >&2
        exit 1
        ;;
esac
