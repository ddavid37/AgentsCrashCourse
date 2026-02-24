#!/usr/bin/env bash
# ============================================================
# CourseWorks Watcher — One-time setup script
# Run this ONCE in your WSL terminal:
#   bash "Daniel's projects/courseworks_watcher/setup.sh"
# ============================================================

set -euo pipefail

PROJECT_ROOT="/home/daniel/projects/AgentsCrashCourse"
SCRIPT_DIR="$PROJECT_ROOT/Daniel's projects/courseworks_watcher"
WATCHER="$SCRIPT_DIR/run_watcher.sh"
LOG="$SCRIPT_DIR/watcher.log"

echo ""
echo "=============================================="
echo "  CourseWorks File Watcher — Setup"
echo "=============================================="

# ── 1. Make sure cron service is running (WSL needs manual start) ─────────────
echo ""
echo "[1/4] Starting cron service..."
if sudo service cron status &>/dev/null; then
    echo "  cron is already running."
else
    sudo service cron start
    echo "  cron started."
fi

# ── 2. Run --init to catalog existing files (prevents re-downloading them) ────
echo ""
echo "[2/4] Cataloging existing files (no downloads on first run)..."
cd "$PROJECT_ROOT"
/home/daniel/.local/bin/uv run python "$SCRIPT_DIR/watcher.py" --init

# ── 3. Install cron job (8pm EST / 9pm EDT every day) ────────────────────────
echo ""
echo "[3/4] Installing daily cron job (8:00 PM America/New_York)..."

CRON_LINE="0 20 * * * TZ=America/New_York $WATCHER >> $LOG 2>&1"

# Remove any previous version of this job, then add fresh
( crontab -l 2>/dev/null | grep -v "courseworks_watcher" ; echo "$CRON_LINE" ) | crontab -

echo "  Cron job installed:"
crontab -l | grep "courseworks_watcher"

# ── 4. Quick sanity check ─────────────────────────────────────────────────────
echo ""
echo "[4/4] Verifying cron can reach the script..."
if [ -x "$WATCHER" ]; then
    echo "  run_watcher.sh is executable — OK"
else
    echo "  Making run_watcher.sh executable..."
    chmod +x "$WATCHER"
fi

echo ""
echo "=============================================="
echo "  Setup complete!"
echo ""
echo "  The watcher will run every day at 8 PM EST."
echo "  Logs:     $LOG"
echo "  Tracking: $SCRIPT_DIR/downloaded_files.json"
echo ""
echo "  To run manually right now:"
echo "    bash \"$WATCHER\""
echo ""
echo "  IMPORTANT — SendGrid sender verification:"
echo "  If emails fail, go to https://app.sendgrid.com/settings/sender_auth"
echo "  and add dd3269@columbia.edu as a verified sender."
echo "=============================================="
