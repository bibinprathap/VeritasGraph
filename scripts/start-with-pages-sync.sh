#!/bin/bash
# VeritasGraph - Auto-update GitHub Pages redirect with Cloudflare Tunnel URL
# This script starts the app, creates a tunnel, and updates the demo redirect page
# The README stays unchanged - only docs/demo/index.html is updated

set -e

# =============================================================================
# CONFIGURATION - UPDATE THESE VALUES
# =============================================================================
# Load GITHUB_TOKEN from .env file if not already set in environment
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env"
if [ -f "$ENV_FILE" ]; then
    export $(grep -E '^GITHUB_TOKEN=' "$ENV_FILE" | xargs)
fi

if [ -z "$GITHUB_TOKEN" ]; then
    echo "ERROR: GITHUB_TOKEN is not set. Add it to .env file: GITHUB_TOKEN=your_token"
    exit 1
fi

GITHUB_REPO="bibinprathap/VeritasGraph"
GITHUB_BRANCH="restored-main"
REDIRECT_FILE_PATH="docs/demo/index.html"

PROJECT_DIR="/home/sijo/VeritasGraph/graphrag-ollama-config"
PYTHON_PATH="/home/sijo/VeritasGraph/.venv/bin/python"
LOG_FILE="/home/sijo/VeritasGraph/veritasgraph.log"

# =============================================================================
# DO NOT EDIT BELOW THIS LINE
# =============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOG_FILE"
}

# Function to update GitHub Pages redirect (uses git push - works with fine-grained PATs)
update_github_redirect() {
    local DEMO_URL=$1
    local NOW
    NOW=$(date -u '+%Y-%m-%d %H:%M UTC')

    log "${YELLOW}📝 Updating GitHub Pages redirect via git...${NC}"

    # Write the updated redirect HTML directly into the repo's docs/demo/index.html
    cat > "$SCRIPT_DIR/../$REDIRECT_FILE_PATH" << HTMLEOF
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <!-- DEMO_URL: ${DEMO_URL} -->
    <meta http-equiv="refresh" content="0;url=${DEMO_URL}">
    <title>VeritasGraph Live Demo - Redirecting...</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .container { text-align: center; padding: 40px; max-width: 500px; }
        h1 { font-size: 2.5rem; margin-bottom: 20px; }
        .spinner {
            border: 4px solid rgba(255,255,255,0.3);
            border-top: 4px solid white;
            border-radius: 50%;
            width: 50px; height: 50px;
            animation: spin 1s linear infinite;
            margin: 30px auto;
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        p { font-size: 1.2rem; margin-bottom: 20px; opacity: 0.9; }
        a {
            display: inline-block; color: white;
            background: rgba(255,255,255,0.2); padding: 15px 30px;
            border-radius: 8px; text-decoration: none;
            font-weight: 600; transition: background 0.3s;
        }
        a:hover { background: rgba(255,255,255,0.3); }
        .status {
            margin-top: 30px; padding: 15px;
            background: rgba(255,255,255,0.1);
            border-radius: 8px; font-size: 0.9rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 VeritasGraph Demo</h1>
        <div class="spinner"></div>
        <p>Redirecting to live demo...</p>
        <a href="${DEMO_URL}">Click here if not redirected</a>
        <div class="status">
            <strong>Status:</strong> Server is online<br>
            <small>Last updated: ${NOW}</small>
        </div>
    </div>
    <script>
        setTimeout(function() { window.location.href = "${DEMO_URL}"; }, 2000);
    </script>
</body>
</html>
HTMLEOF

    # Commit and push via git using the token
    cd "$SCRIPT_DIR/.."
    REMOTE_URL="https://${GITHUB_TOKEN}@github.com/${GITHUB_REPO}.git"

    # Configure git user identity if not already set (required for commits in automated environments)
    if ! git config user.email > /dev/null 2>&1; then
        git config user.email "veritasgraph@localhost"
        git config user.name "VeritasGraph Auto-Updater"
    fi

    # Fetch and checkout the target branch
    git fetch origin "$GITHUB_BRANCH" 2>/dev/null || true
    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    if [ "$CURRENT_BRANCH" != "$GITHUB_BRANCH" ]; then
        git checkout "$GITHUB_BRANCH" 2>/dev/null || git checkout -B "$GITHUB_BRANCH" "origin/$GITHUB_BRANCH"
    fi
    # Pull latest changes from remote
    git pull origin "$GITHUB_BRANCH" --rebase 2>/dev/null || true

    git add "$REDIRECT_FILE_PATH"
    if git diff --cached --quiet; then
        log "No change in redirect URL, skipping commit."
        return 0
    fi

    git commit -m "🔄 Update demo redirect: ${DEMO_URL}"
    git push "$REMOTE_URL" "$GITHUB_BRANCH"

    if [ $? -eq 0 ]; then
        log "${GREEN}✅ GitHub Pages redirect updated!${NC}"
        log "${CYAN}📍 Stable URL: https://bibinprathap.github.io/VeritasGraph/demo/${NC}"
        log "${CYAN}📍 Current tunnel: ${DEMO_URL}${NC}"
        return 0
    else
        error "Failed to push redirect update."
        return 1
    fi
}

# Function to extract Cloudflare URL from output
extract_cf_url() {
    grep -oP 'https://[a-z0-9-]+\.trycloudflare\.com' | head -1
}

# Main function
main() {
    log "============================================"
    log "🚀 VeritasGraph - Starting with GitHub Pages Sync"
    log "============================================"
    
    # Start the Gradio app in background
    log "Starting VeritasGraph app..."
    cd "$PROJECT_DIR"
    $PYTHON_PATH app.py &
    APP_PID=$!
    
    # Wait for app to start
    sleep 5
    
    # Check if app is running
    if ! kill -0 $APP_PID 2>/dev/null; then
        error "App failed to start!"
        exit 1
    fi
    
    log "✅ App started on port 7860"
    
    # Handle shutdown
    trap "log 'Shutting down...'; kill $APP_PID 2>/dev/null; exit 0" SIGINT SIGTERM

    # Start Cloudflare tunnel and monitor output in the current shell (no subshell)
    # Using process substitution < <(...) keeps the while loop in the current shell,
    # so update_github_redirect can log errors and git operations are visible.
    log "Starting Cloudflare tunnel..."
    URL_FOUND=false
    while IFS= read -r line; do
        # Strip ANSI escape codes that cloudflared injects (breaks grep/regex)
        clean_line=$(printf '%s' "$line" | sed 's/\x1b\[[0-9;]*[mGKHFJl]//g')
        echo "$clean_line" | tee -a "$LOG_FILE"

        # Extract the tunnel URL when it first appears; skip if already found
        if [ "$URL_FOUND" = "false" ] && echo "$clean_line" | grep -q "trycloudflare.com"; then
            TUNNEL_URL=$(echo "$clean_line" | grep -oP 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' | head -1)
            if [ -n "$TUNNEL_URL" ]; then
                URL_FOUND=true
                log "✅ Tunnel URL: $TUNNEL_URL"

                # Update GitHub Pages redirect
                if update_github_redirect "$TUNNEL_URL"; then
                    log "🌐 Server is running. Press Ctrl+C to stop."
                else
                    error "GitHub Pages update failed — check token permissions and git config"
                fi
            fi
        fi
    done < <(cloudflared tunnel --url http://localhost:7860 2>&1)

    # Tunnel exited — stop the app too
    log "Cloudflare tunnel exited. Stopping app..."
    kill $APP_PID 2>/dev/null || true
}

main "$@"
