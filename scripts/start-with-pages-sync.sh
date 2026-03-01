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
GITHUB_BRANCH="master"
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

# Function to update GitHub Pages redirect
update_github_redirect() {
    local DEMO_URL=$1
    
    log "${YELLOW}📝 Updating GitHub Pages redirect...${NC}"
    
    # Get current file content and SHA
    RESPONSE=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
        -H "Accept: application/vnd.github.v3+json" \
        "https://api.github.com/repos/$GITHUB_REPO/contents/$REDIRECT_FILE_PATH?ref=$GITHUB_BRANCH")
    
    CURRENT_SHA=$(echo "$RESPONSE" | grep -o '"sha": "[^"]*"' | head -1 | cut -d'"' -f4)
    
    if [ -z "$CURRENT_SHA" ]; then
        error "Failed to get file SHA. Check your GitHub token."
        return 1
    fi
    
    # Create new redirect HTML content
    NEW_CONTENT=$(cat << EOF
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
        .container {
            text-align: center;
            padding: 40px;
            max-width: 500px;
        }
        h1 { font-size: 2.5rem; margin-bottom: 20px; }
        .spinner {
            border: 4px solid rgba(255,255,255,0.3);
            border-top: 4px solid white;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
            margin: 30px auto;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        p { font-size: 1.2rem; margin-bottom: 20px; opacity: 0.9; }
        a {
            display: inline-block;
            color: white;
            background: rgba(255,255,255,0.2);
            padding: 15px 30px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 600;
            transition: background 0.3s;
        }
        a:hover { background: rgba(255,255,255,0.3); }
        .status {
            margin-top: 30px;
            padding: 15px;
            background: rgba(255,255,255,0.1);
            border-radius: 8px;
            font-size: 0.9rem;
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
            <small>Last updated: $(date -u '+%Y-%m-%d %H:%M UTC')</small>
        </div>
    </div>
    <script>
        setTimeout(function() {
            window.location.href = "${DEMO_URL}";
        }, 2000);
    </script>
</body>
</html>
EOF
)
    
    # Encode content to base64
    ENCODED_CONTENT=$(echo "$NEW_CONTENT" | base64 -w 0)
    
    # Update file via GitHub API
    UPDATE_RESPONSE=$(curl -s -X PUT \
        -H "Authorization: token $GITHUB_TOKEN" \
        -H "Accept: application/vnd.github.v3+json" \
        "https://api.github.com/repos/$GITHUB_REPO/contents/$REDIRECT_FILE_PATH" \
        -d "{
            \"message\": \"🔄 Update demo redirect: ${DEMO_URL}\",
            \"content\": \"${ENCODED_CONTENT}\",
            \"sha\": \"${CURRENT_SHA}\",
            \"branch\": \"${GITHUB_BRANCH}\"
        }")
    
    if echo "$UPDATE_RESPONSE" | grep -q '"commit"'; then
        log "${GREEN}✅ GitHub Pages redirect updated!${NC}"
        log "${CYAN}📍 Stable URL: https://bibinprathap.github.io/VeritasGraph/demo/${NC}"
        log "${CYAN}📍 Current tunnel: ${DEMO_URL}${NC}"
        return 0
    else
        error "Failed to update redirect: $UPDATE_RESPONSE"
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
    
    # Start Cloudflare tunnel
    log "Starting Cloudflare tunnel..."
    cloudflared tunnel --url http://localhost:7860 2>&1 | while read line; do
        echo "$line"
        
        # Extract the tunnel URL when it appears
        if echo "$line" | grep -q "trycloudflare.com"; then
            TUNNEL_URL=$(echo "$line" | extract_cf_url)
            if [ -n "$TUNNEL_URL" ]; then
                log "✅ Tunnel URL: $TUNNEL_URL"
                
                # Update GitHub Pages redirect
                update_github_redirect "$TUNNEL_URL"
                
                log "🌐 Server is running. Press Ctrl+C to stop."
            fi
        fi
    done &
    TUNNEL_PID=$!
    
    # Wait a bit for tunnel to establish
    log "⏳ Waiting for Cloudflare tunnel URL..."
    sleep 10
    
    # Handle shutdown
    trap "log 'Shutting down...'; kill $APP_PID $TUNNEL_PID 2>/dev/null; exit 0" SIGINT SIGTERM
    
    # Keep running
    wait $APP_PID
}

main "$@"
