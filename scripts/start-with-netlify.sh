#!/bin/bash
# VeritasGraph - Auto-start with Netlify URL updater
# This script starts the Gradio app and updates the Netlify redirect

set -e

# Configuration - UPDATE THESE VALUES
NETLIFY_SITE_ID="your-site-id"  # Get from Netlify dashboard
NETLIFY_AUTH_TOKEN="your-netlify-token"  # Get from Netlify > User Settings > Applications > Personal Access Tokens
PROJECT_DIR="/home/ubuntu/VeritasGraph/graphrag-ollama-config"
PYTHON_PATH="/home/ubuntu/VeritasGraph/.venv/bin/python"
LOG_FILE="/var/log/veritasgraph.log"
REDIRECT_FILE="/tmp/netlify_redirects/_redirects"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}🚀 VeritasGraph - Starting with Netlify Sync${NC}"
echo -e "${GREEN}============================================${NC}"

# Create temp directory for Netlify deploy
mkdir -p /tmp/netlify_redirects

# Function to extract Gradio URL from output
extract_gradio_url() {
    grep -oP 'https://[a-z0-9]+\.gradio\.live' | head -1
}

# Function to update Netlify redirect
update_netlify_redirect() {
    local GRADIO_URL=$1
    
    echo -e "${YELLOW}📡 Updating Netlify redirect to: ${GRADIO_URL}${NC}"
    
    # Create _redirects file
    cat > "$REDIRECT_FILE" << EOF
# VeritasGraph Demo Redirect
# Auto-updated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# Current Gradio URL: ${GRADIO_URL}

/   ${GRADIO_URL}   302
/*  ${GRADIO_URL}   302
EOF

    # Create a simple index.html as fallback
    cat > /tmp/netlify_redirects/index.html << EOF
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="0;url=${GRADIO_URL}">
    <title>VeritasGraph Demo</title>
    <style>
        body { font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
        .container { text-align: center; padding: 40px; }
        h1 { font-size: 2.5rem; margin-bottom: 20px; }
        p { font-size: 1.2rem; margin-bottom: 30px; }
        a { color: #fff; background: rgba(255,255,255,0.2); padding: 15px 30px; border-radius: 8px; text-decoration: none; font-weight: bold; }
        a:hover { background: rgba(255,255,255,0.3); }
        .spinner { border: 4px solid rgba(255,255,255,0.3); border-top: 4px solid white; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 20px auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 VeritasGraph Demo</h1>
        <div class="spinner"></div>
        <p>Redirecting to live demo...</p>
        <p><a href="${GRADIO_URL}">Click here if not redirected</a></p>
    </div>
</body>
</html>
EOF

    # Deploy to Netlify using their CLI or API
    if command -v netlify &> /dev/null; then
        # Using Netlify CLI
        cd /tmp/netlify_redirects
        netlify deploy --prod --dir=. --site="$NETLIFY_SITE_ID" --auth="$NETLIFY_AUTH_TOKEN"
    else
        # Using Netlify API directly with curl
        echo -e "${YELLOW}Deploying via Netlify API...${NC}"
        
        # Create a zip of the files
        cd /tmp/netlify_redirects
        zip -r deploy.zip . -x "*.zip"
        
        # Deploy via API
        curl -s -X POST "https://api.netlify.com/api/v1/sites/${NETLIFY_SITE_ID}/deploys" \
            -H "Authorization: Bearer ${NETLIFY_AUTH_TOKEN}" \
            -H "Content-Type: application/zip" \
            --data-binary "@deploy.zip" > /dev/null
        
        rm deploy.zip
    fi
    
    echo -e "${GREEN}✅ Netlify redirect updated successfully!${NC}"
}

# Function to monitor and update
monitor_gradio() {
    local TEMP_LOG=$(mktemp)
    
    # Start Gradio and capture output
    cd "$PROJECT_DIR"
    $PYTHON_PATH app.py --share --host 0.0.0.0 --port 7860 2>&1 | tee "$TEMP_LOG" &
    GRADIO_PID=$!
    
    echo -e "${YELLOW}⏳ Waiting for Gradio share URL...${NC}"
    
    # Wait for the gradio.live URL to appear
    for i in {1..60}; do
        sleep 2
        GRADIO_URL=$(cat "$TEMP_LOG" | extract_gradio_url)
        if [ -n "$GRADIO_URL" ]; then
            echo -e "${GREEN}✅ Got Gradio URL: ${GRADIO_URL}${NC}"
            update_netlify_redirect "$GRADIO_URL"
            break
        fi
        echo -n "."
    done
    
    if [ -z "$GRADIO_URL" ]; then
        echo -e "${RED}❌ Failed to get Gradio share URL after 2 minutes${NC}"
    fi
    
    # Keep the script running
    wait $GRADIO_PID
}

# Main execution
monitor_gradio
