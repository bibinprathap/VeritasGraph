#!/usr/bin/env pwsh
# VeritasGraph - Start Server with Public URL
# This script starts the Gradio app and creates a public shareable link

param(
    [switch]$Share,
    [switch]$Ngrok,
    [int]$Port = 7860
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "🚀 VeritasGraph - GraphRAG Demo Server" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Check if virtual environment exists
$VenvPath = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPath)) {
    $VenvPath = Join-Path (Split-Path $ProjectRoot) ".venv\Scripts\python.exe"
}

if (-not (Test-Path $VenvPath)) {
    Write-Host "❌ Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please create a virtual environment first:" -ForegroundColor Yellow
    Write-Host "  python -m venv .venv" -ForegroundColor White
    Write-Host "  .venv\Scripts\pip install -r requirements.txt" -ForegroundColor White
    exit 1
}

Set-Location (Join-Path $ProjectRoot "graphrag-ollama-config")

if ($Ngrok) {
    Write-Host ""
    Write-Host "📡 Starting with Ngrok tunnel..." -ForegroundColor Green
    Write-Host "Make sure ngrok is installed: winget install ngrok.ngrok" -ForegroundColor Yellow
    Write-Host ""
    
    # Start the app in background
    $AppJob = Start-Job -ScriptBlock {
        param($VenvPath, $Port)
        & $VenvPath app.py --host 0.0.0.0 --port $Port
    } -ArgumentList $VenvPath, $Port
    
    Start-Sleep -Seconds 3
    
    Write-Host "Starting ngrok tunnel on port $Port..." -ForegroundColor Cyan
    ngrok http $Port
    
} elseif ($Share) {
    Write-Host ""
    Write-Host "📡 Creating Gradio share link (valid for 72 hours)..." -ForegroundColor Green
    Write-Host ""
    & $VenvPath app.py --share --host 0.0.0.0 --port $Port
    
} else {
    Write-Host ""
    Write-Host "🌐 Starting local server on port $Port..." -ForegroundColor Green
    Write-Host "Access at: http://localhost:$Port" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "To create a public link, use one of these options:" -ForegroundColor Yellow
    Write-Host "  .\start-server.ps1 -Share   # Gradio share (72h)" -ForegroundColor White
    Write-Host "  .\start-server.ps1 -Ngrok   # Ngrok tunnel" -ForegroundColor White
    Write-Host ""
    & $VenvPath app.py --host 0.0.0.0 --port $Port
}
