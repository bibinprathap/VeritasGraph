# VeritasGraph - Linux Server Deployment with Netlify Redirect

This guide explains how to deploy VeritasGraph on a Linux server with a **persistent URL** on Netlify that auto-updates when your Gradio share link changes.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Users access: veritasgraph-demo.netlify.app                    │
│                           │                                      │
│                           ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              Netlify (Static Redirect)                   │    │
│  │  _redirects: / → https://xxx.gradio.live 302            │    │
│  └─────────────────────────────────────────────────────────┘    │
│                           │                                      │
│                           ▼ (auto-updated on restart)           │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │            Your Linux Server                             │    │
│  │  ┌─────────────┐    ┌─────────────┐                     │    │
│  │  │   Ollama    │◄───│  Gradio App │ --share             │    │
│  │  │  (LLM)      │    │  (GraphRAG) │───► gradio.live     │    │
│  │  └─────────────┘    └─────────────┘                     │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## Step 1: Set Up Netlify Site

1. **Create a Netlify account** at https://netlify.com (free)

2. **Create a new site:**
   - Go to Sites → Add new site → Deploy manually
   - Upload a simple index.html (we'll auto-update it later)
   - Note your **Site ID** from Site Settings → General

3. **Get your Personal Access Token:**
   - Go to User Settings → Applications → Personal Access Tokens
   - Create a new token with full access
   - Save this token securely

4. **Custom domain (optional):**
   - Go to Domain settings
   - Add a custom domain like `demo.yourdomain.com`

## Step 2: Set Up Linux Server

### Prerequisites

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11+
sudo apt install python3.11 python3.11-venv python3-pip -y

# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull required models
ollama pull llama3.1
ollama pull nomic-embed-text
ollama create llama3.1-12k -f Modelfile
```

### Clone and Set Up VeritasGraph

```bash
cd /home/ubuntu
git clone https://github.com/bibinprathap/VeritasGraph.git
cd VeritasGraph

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r graphrag-ollama-config/requirements.txt
```

### Configure Environment

```bash
cd graphrag-ollama-config

# Copy and edit .env
cp .env.example .env
nano .env
```

Set your configuration:
```env
# For local Ollama
GRAPHRAG_API_KEY=ollama
GRAPHRAG_LLM_MODEL=llama3.1-12k
GRAPHRAG_LLM_API_BASE=http://localhost:11434/v1
GRAPHRAG_EMBEDDING_MODEL=nomic-embed-text
GRAPHRAG_EMBEDDING_API_BASE=http://localhost:11434/v1
GRAPHRAG_EMBEDDING_API_KEY=ollama
```

### Configure the Startup Script

```bash
# Edit the startup script
nano /home/ubuntu/VeritasGraph/scripts/start-with-netlify.sh

# Update these variables:
NETLIFY_SITE_ID="your-actual-site-id"
NETLIFY_AUTH_TOKEN="your-actual-token"
PROJECT_DIR="/home/ubuntu/VeritasGraph/graphrag-ollama-config"
PYTHON_PATH="/home/ubuntu/VeritasGraph/.venv/bin/python"

# Make it executable
chmod +x /home/ubuntu/VeritasGraph/scripts/start-with-netlify.sh
```

## Step 3: Set Up Systemd Service (Auto-start on Boot)

```bash
# Copy the service file
sudo cp /home/ubuntu/VeritasGraph/scripts/veritasgraph.service /etc/systemd/system/

# Edit with your credentials
sudo nano /etc/systemd/system/veritasgraph.service

# Update Environment lines:
Environment="NETLIFY_SITE_ID=your-site-id"
Environment="NETLIFY_AUTH_TOKEN=your-token"

# Reload systemd
sudo systemctl daemon-reload

# Enable auto-start on boot
sudo systemctl enable veritasgraph

# Start the service
sudo systemctl start veritasgraph

# Check status
sudo systemctl status veritasgraph

# View logs
sudo journalctl -u veritasgraph -f
```

## Step 4: Test the Setup

1. **Check the service is running:**
   ```bash
   sudo systemctl status veritasgraph
   ```

2. **Check the logs:**
   ```bash
   tail -f /var/log/veritasgraph.log
   ```

3. **Visit your Netlify URL:**
   - Go to `https://your-site-name.netlify.app`
   - It should redirect to your current Gradio share URL

4. **Test restart:**
   ```bash
   sudo systemctl restart veritasgraph
   # Wait 30 seconds, then check if Netlify is updated
   ```

## How It Works

1. **On startup**, the script runs `python app.py --share`
2. Gradio generates a temporary URL like `https://abc123.gradio.live`
3. The script **captures this URL** from the output
4. It creates a `_redirects` file and deploys to Netlify
5. Users visiting `your-site.netlify.app` are redirected to the live demo
6. On **restart**, the process repeats with the new URL

## Troubleshooting

### Gradio URL not updating
```bash
# Check if the script is extracting the URL correctly
grep "gradio.live" /var/log/veritasgraph.log
```

### Netlify deploy failing
```bash
# Test Netlify API manually
curl -X GET "https://api.netlify.com/api/v1/sites" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Service not starting
```bash
# Check detailed logs
sudo journalctl -u veritasgraph -n 100 --no-pager
```

## Security Notes

1. **Never commit tokens to git** - use environment variables
2. **Use HTTPS** - Gradio share URLs are always HTTPS
3. **Consider IP restrictions** if needed
4. **Rotate tokens** periodically

## Alternative: Use Cloudflare Tunnel (More Stable)

For a more permanent solution without relying on Gradio's share feature:

```bash
# Install cloudflared
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared
chmod +x cloudflared
sudo mv cloudflared /usr/local/bin/

# Create tunnel (requires Cloudflare account)
cloudflared tunnel create veritasgraph
cloudflared tunnel route dns veritasgraph demo.yourdomain.com

# Run tunnel
cloudflared tunnel run --url http://localhost:7860 veritasgraph
```

This gives you a **permanent URL** without needing to update Netlify!
