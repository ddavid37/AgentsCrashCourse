#!/usr/bin/env bash
# Wrapper script called by cron.
# Uses uv to run watcher.py inside the project's virtual environment.

set -euo pipefail

PROJECT_ROOT="/home/daniel/projects/AgentsCrashCourse"
SCRIPT_DIR="$PROJECT_ROOT/Daniel's projects/courseworks_watcher"

cd "$PROJECT_ROOT"
/home/daniel/.local/bin/uv run python "$SCRIPT_DIR/watcher.py" "$@"
