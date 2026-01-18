#!/bin/bash
# VeritasGraph - Auto-update GitHub README with Cloudflare Tunnel URL
# This script starts the app, creates a tunnel, and updates GitHub README

set -e

# =============================================================================
# CONFIGURATION - UPDATE THESE VALUES
# =============================================================================
GITHUB_TOKEN="your-github-personal-access-token"  # Create at: github.com/settings/tokens
GITHUB_REPO="bibinprathap/VeritasGraph"           # Your repo
GITHUB_BRANCH="master"                             # or "main"
README_PATH="README.md"

PROJECT_DIR="/home/ubuntu/VeritasGraph/graphrag-ollama-config"
PYTHON_PATH="/home/ubuntu/VeritasGraph/.venv/bin/python"
LOG_FILE="/var/log/veritasgraph.log"

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

# Function to update GitHub README
update_github_readme() {
    local DEMO_URL=$1
    
    log "${YELLOW}📝 Updating GitHub README with new demo URL...${NC}"
    
    # Get current README content and SHA
    RESPONSE=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
        -H "Accept: application/vnd.github.v3+json" \
        "https://api.github.com/repos/$GITHUB_REPO/contents/$README_PATH?ref=$GITHUB_BRANCH")
    
    CURRENT_SHA=$(echo "$RESPONSE" | grep -o '"sha": "[^"]*"' | head -1 | cut -d'"' -f4)
    CURRENT_CONTENT=$(echo "$RESPONSE" | grep -o '"content": "[^"]*"' | cut -d'"' -f4 | base64 -d 2>/dev/null || echo "")
    
    if [ -z "$CURRENT_SHA" ]; then
        error "Failed to get README SHA. Check your GitHub token."
        return 1
    fi
    
    # Update the demo link in README
    # Look for the pattern: <!-- DEMO_URL_START -->...<!-- DEMO_URL_END -->
    # Or update the commented demo link
    
    NEW_CONTENT=$(echo "$CURRENT_CONTENT" | sed -E "s|<!-- DEMO_URL_START -->.*<!-- DEMO_URL_END -->|<!-- DEMO_URL_START -->\n\n**[🎮 Try Live Demo](${DEMO_URL})** - *Last updated: $(date -u '+%Y-%m-%d %H:%M UTC')*\n\n<!-- DEMO_URL_END -->|g")
    
    # If no markers found, try to update the commented line
    if [ "$NEW_CONTENT" == "$CURRENT_CONTENT" ]; then
        NEW_CONTENT=$(echo "$CURRENT_CONTENT" | sed -E "s|<!-- \*\*\[🎮 Try Live Demo\].*\*\* -->|**[🎮 Try Live Demo](${DEMO_URL})** - *Last updated: $(date -u '+%Y-%m-%d %H:%M UTC')*|g")
    fi
    
    # Encode content to base64
    ENCODED_CONTENT=$(echo "$NEW_CONTENT" | base64 -w 0)
    
    # Update README via GitHub API
    UPDATE_RESPONSE=$(curl -s -X PUT \
        -H "Authorization: token $GITHUB_TOKEN" \
        -H "Accept: application/vnd.github.v3+json" \
        "https://api.github.com/repos/$GITHUB_REPO/contents/$README_PATH" \
        -d "{
            \"message\": \"🤖 Auto-update demo URL: ${DEMO_URL}\",
            \"content\": \"${ENCODED_CONTENT}\",
            \"sha\": \"${CURRENT_SHA}\",
            \"branch\": \"${GITHUB_BRANCH}\"
        }")
    
    if echo "$UPDATE_RESPONSE" | grep -q '"commit"'; then
        log "${GREEN}✅ GitHub README updated successfully!${NC}"
        log "${CYAN}📍 Demo URL: ${DEMO_URL}${NC}"
        return 0
    else
        error "Failed to update README: $UPDATE_RESPONSE"
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
    log "🚀 VeritasGraph - Starting with GitHub Sync"
    log "============================================"
    
    # Start the Gradio app in background
    log "Starting VeritasGraph app..."
    cd "$PROJECT_DIR"
    $PYTHON_PATH app.py --host 0.0.0.0 --port 7860 &
    APP_PID=$!
    
    # Wait for app to start
    sleep 5
    
    # Check if app is running
    if ! kill -0 $APP_PID 2>/dev/null; then
        error "Failed to start VeritasGraph app"
        exit 1
    fi
    
    log "${GREEN}✅ App started on port 7860${NC}"
    
    # Start Cloudflare tunnel and capture URL
    log "Starting Cloudflare tunnel..."
    
    TEMP_LOG=$(mktemp)
    cloudflared tunnel --url http://localhost:7860 2>&1 | tee "$TEMP_LOG" &
    CF_PID=$!
    
    # Wait for tunnel URL to appear
    log "⏳ Waiting for Cloudflare tunnel URL..."
    CF_URL=""
    for i in {1..30}; do
        sleep 2
        CF_URL=$(cat "$TEMP_LOG" | extract_cf_url)
        if [ -n "$CF_URL" ]; then
            break
        fi
        echo -n "."
    done
    echo ""
    
    if [ -z "$CF_URL" ]; then
        error "Failed to get Cloudflare tunnel URL after 60 seconds"
        # Keep running anyway
    else
        log "${GREEN}✅ Tunnel URL: ${CF_URL}${NC}"
        
        # Update GitHub README
        update_github_readme "$CF_URL"
    fi
    
    # Wait for processes
    log "🌐 Server is running. Press Ctrl+C to stop."
    wait $APP_PID $CF_PID
}

# Cleanup on exit
cleanup() {
    log "Shutting down..."
    kill $APP_PID 2>/dev/null || true
    kill $CF_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# Run main
main
