#!/bin/bash
# VeritasGraph Studio - Auto-publish a Cloudflare Tunnel demo link
# -----------------------------------------------------------------
# Starts the studio_api FastAPI server, opens a Cloudflare quick tunnel,
# then rewrites docs/studio/index.html with the new public URL and pushes
# it to GitHub. The stable demo link stays the same:
#   https://bibinprathap.github.io/VeritasGraph/studio/
# Only docs/studio/index.html changes each run (the README is untouched).
#
# Designed to be launched on boot via the systemd unit in this folder.

set -euo pipefail

# =============================================================================
# CONFIGURATION
# =============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Load GITHUB_TOKEN from .env if not already in the environment
ENV_FILE="$REPO_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    # shellcheck disable=SC2046
    export $(grep -E '^GITHUB_TOKEN=' "$ENV_FILE" | xargs) || true
fi

if [ -z "${GITHUB_TOKEN:-}" ]; then
    echo "ERROR: GITHUB_TOKEN is not set. Add it to .env: GITHUB_TOKEN=your_token"
    exit 1
fi

GITHUB_REPO="bibinprathap/VeritasGraph"
GITHUB_BRANCH="master"
REDIRECT_FILE_PATH="docs/studio/index.html"

STUDIO_HOST="127.0.0.1"
STUDIO_PORT="8200"
PYTHON_BIN="$REPO_DIR/.venv/bin/python"
UVICORN_BIN="$REPO_DIR/.venv/bin/uvicorn"
LOG_FILE="$REPO_DIR/studio-tunnel.log"

# Studio runtime knobs (kept in sync with studio_api/README.md)
export STUDIO_DATA_DIR="${STUDIO_DATA_DIR:-$REPO_DIR/studio_api/data}"
export STUDIO_EVAL_STEP_SECONDS="${STUDIO_EVAL_STEP_SECONDS:-2}"
export STUDIO_FT_STEP_SECONDS="${STUDIO_FT_STEP_SECONDS:-3}"

# =============================================================================
# DO NOT EDIT BELOW THIS LINE
# =============================================================================
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

log()   { echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"        | tee -a "$LOG_FILE"; }
warn()  { echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARN:${NC} $1" | tee -a "$LOG_FILE"; }
error() { echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"   | tee -a "$LOG_FILE"; }

APP_PID=""
TUNNEL_PID=""

cleanup() {
    log "Shutting down..."
    [ -n "$TUNNEL_PID" ] && kill "$TUNNEL_PID" 2>/dev/null || true
    [ -n "$APP_PID" ]    && kill "$APP_PID"    2>/dev/null || true
    exit 0
}
trap cleanup SIGINT SIGTERM

# -----------------------------------------------------------------------------
# Rewrite docs/studio/index.html and push it to GitHub
# -----------------------------------------------------------------------------
update_github_redirect() {
    local DEMO_URL="$1"
    local NOW
    NOW=$(date -u '+%Y-%m-%d %H:%M UTC')

    log "${YELLOW}Updating GitHub Pages studio redirect via git...${NC}"

    mkdir -p "$REPO_DIR/$(dirname "$REDIRECT_FILE_PATH")"
    cat > "$REPO_DIR/$REDIRECT_FILE_PATH" << HTMLEOF
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <!-- DEMO_URL: ${DEMO_URL} -->
    <meta http-equiv="refresh" content="0;url=${DEMO_URL}/studio">
    <title>VeritasGraph Studio - Live Demo</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            background: linear-gradient(135deg, #1e3a8a 0%, #6d28d9 100%);
            color: white;
        }
        .container { text-align: center; padding: 40px; max-width: 520px; }
        h1 { font-size: 2.4rem; margin-bottom: 16px; }
        .sub { font-size: 1.05rem; opacity: 0.85; margin-bottom: 24px; }
        .spinner {
            border: 4px solid rgba(255,255,255,0.3);
            border-top: 4px solid white;
            border-radius: 50%;
            width: 50px; height: 50px;
            animation: spin 1s linear infinite;
            margin: 28px auto;
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        p { font-size: 1.2rem; margin-bottom: 20px; opacity: 0.9; }
        a {
            display: inline-block; color: white;
            background: rgba(255,255,255,0.2); padding: 15px 30px;
            border-radius: 8px; text-decoration: none;
            font-weight: 600; transition: background 0.3s;
        }
        a:hover { background: rgba(255,255,255,0.32); }
        .status {
            margin-top: 30px; padding: 15px;
            background: rgba(255,255,255,0.1);
            border-radius: 8px; font-size: 0.9rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🧩 VeritasGraph Studio</h1>
        <div class="sub">Build, wire &amp; test GraphRAG agents — live demo</div>
        <div class="spinner"></div>
        <p>Redirecting to the live studio...</p>
        <a href="${DEMO_URL}/studio">Click here if not redirected</a>
        <div class="status">
            <strong>Status:</strong> Server is online<br>
            <small>Last updated: ${NOW}</small>
        </div>
    </div>
    <script>
        setTimeout(function() { window.location.href = "${DEMO_URL}/studio"; }, 2000);
    </script>
</body>
</html>
HTMLEOF

    cd "$REPO_DIR"
    local REMOTE_URL="https://${GITHUB_TOKEN}@github.com/${GITHUB_REPO}.git"

    if ! git config user.email > /dev/null 2>&1; then
        git config user.email "veritasgraph@localhost"
        git config user.name "VeritasGraph Auto-Updater"
    fi

    git fetch origin "$GITHUB_BRANCH" 2>/dev/null || true
    local CURRENT_BRANCH
    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    if [ "$CURRENT_BRANCH" != "$GITHUB_BRANCH" ]; then
        git checkout "$GITHUB_BRANCH" 2>/dev/null || git checkout -B "$GITHUB_BRANCH" "origin/$GITHUB_BRANCH"
    fi
    git pull origin "$GITHUB_BRANCH" --rebase 2>/dev/null || true

    git add "$REDIRECT_FILE_PATH"
    if git diff --cached --quiet; then
        log "No change in studio redirect URL, skipping commit."
        return 0
    fi

    git commit -m "🔄 Update studio demo redirect: ${DEMO_URL}/studio"
    if git push "$REMOTE_URL" "$GITHUB_BRANCH" 2>/dev/null; then
        log "${GREEN}✅ Studio redirect updated!${NC}"
        log "${CYAN}📍 Stable URL: https://bibinprathap.github.io/VeritasGraph/studio/${NC}"
        log "${CYAN}📍 Current tunnel: ${DEMO_URL}/studio${NC}"
        return 0
    fi
    error "Failed to push studio redirect update."
    return 1
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
main() {
    log "============================================"
    log "🚀 VeritasGraph Studio - tunnel + Pages sync"
    log "============================================"

    cd "$REPO_DIR"

    log "Starting studio_api on ${STUDIO_HOST}:${STUDIO_PORT}..."
    "$UVICORN_BIN" studio_api.main:app \
        --host "$STUDIO_HOST" --port "$STUDIO_PORT" --log-level warning \
        >> "$LOG_FILE" 2>&1 &
    APP_PID=$!

    # Wait for the server to answer /health (up to ~30s)
    local ready=false
    for _ in $(seq 1 30); do
        if curl -fsS "http://${STUDIO_HOST}:${STUDIO_PORT}/health" >/dev/null 2>&1; then
            ready=true; break
        fi
        if ! kill -0 "$APP_PID" 2>/dev/null; then
            error "studio_api exited during startup. See $LOG_FILE"
            exit 1
        fi
        sleep 1
    done
    if [ "$ready" != true ]; then
        error "studio_api did not become healthy in time."
        cleanup
    fi
    log "✅ studio_api is healthy."

    log "Starting Cloudflare tunnel..."
    local URL_FOUND=false
    while IFS= read -r line; do
        # Strip ANSI escape codes cloudflared injects
        local clean_line
        clean_line=$(printf '%s' "$line" | sed 's/\x1b\[[0-9;]*[mGKHFJl]//g')
        echo "$clean_line" >> "$LOG_FILE"

        if [ "$URL_FOUND" = false ] && echo "$clean_line" | grep -q "trycloudflare.com"; then
            local TUNNEL_URL
            TUNNEL_URL=$(echo "$clean_line" | grep -oP 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' | head -1)
            if [ -n "$TUNNEL_URL" ]; then
                URL_FOUND=true
                log "✅ Tunnel URL: $TUNNEL_URL"
                if update_github_redirect "$TUNNEL_URL"; then
                    log "🌐 Studio is live. Press Ctrl+C to stop."
                else
                    error "GitHub Pages update failed — check token permissions and git config"
                fi
            fi
        fi
    done < <(cloudflared tunnel --url "http://${STUDIO_HOST}:${STUDIO_PORT}" 2>&1)

    warn "Cloudflare tunnel exited. Stopping studio_api..."
    cleanup
}

main "$@"
