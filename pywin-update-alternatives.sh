#!/usr/bin/env bash
# pywin-update-alternatives.sh — Git Bash / MSYS2 / Cygwin launcher
#
# Locates Python and runs the pywin_update_alternatives package from the
# repository root.  Works in Git Bash on Windows where the embedded Python
# bootstrap (scripts/pywin-update-alternatives.ps1) is not available without
# PowerShell.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"

# ---------------------------------------------------------------------------
# Locate a suitable Python interpreter
# ---------------------------------------------------------------------------
_find_python() {
    local candidates=("python" "python3" "py")
    for py in "${candidates[@]}"; do
        if command -v "$py" &>/dev/null; then
            local ver
            ver=$("$py" -c "import sys; print(sys.version_info >= (3,7))" 2>/dev/null || true)
            if [ "$ver" = "True" ]; then
                echo "$py"
                return 0
            fi
        fi
    done

    # Check the embedded runtime created by the PowerShell bootstrap
    local embedded="$REPO_ROOT/.embedded-python/python.exe"
    if [ -f "$embedded" ]; then
        echo "$embedded"
        return 0
    fi

    echo "Error: Python 3.7+ not found. Install Python or run the PowerShell" >&2
    echo "       bootstrap first: scripts/pywin-update-alternatives.ps1" >&2
    exit 1
}

PYTHON="$(_find_python)"

# ---------------------------------------------------------------------------
# Convert MSYS/Cygwin-style paths in JAVA_HOME / PATH to Windows paths so
# that the Python module sees consistent backslash-separated paths.
# cygpath is available in Git Bash (MSYS2) and Cygwin.
# ---------------------------------------------------------------------------
if command -v cygpath &>/dev/null; then
    if [ -n "${JAVA_HOME:-}" ]; then
        export JAVA_HOME
        JAVA_HOME="$(cygpath -w "$JAVA_HOME")"
    fi
    if [ -n "${JDK_HOME:-}" ]; then
        export JDK_HOME
        JDK_HOME="$(cygpath -w "$JDK_HOME")"
    fi
fi

cd "$REPO_ROOT"
exec "$PYTHON" -m pywin_update_alternatives "$@"
