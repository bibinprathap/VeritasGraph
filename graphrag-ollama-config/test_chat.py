#!/usr/bin/env python3
"""Simple test script for the Gradio chat interface."""
import requests
import json

def test_gradio_api():
    """Test the Gradio API endpoint."""
    base_url = "http://127.0.0.1:7861"
    
    # First, check if the server is responding
    try:
        response = requests.get(f"{base_url}/")
        print(f"✓ Server is running (status: {response.status_code})")
    except requests.exceptions.ConnectionError:
        print("✗ Server is not running. Please start the app first with: python app.py")
        return
    
    # Test the API info endpoint
    try:
        response = requests.get(f"{base_url}/info")
        if response.status_code == 200:
            print(f"✓ API info endpoint is working")
        else:
            print(f"○ API info endpoint returned: {response.status_code}")
    except Exception as e:
        print(f"○ API info: {e}")
    
    # Test the chat function via Gradio's API
    try:
        # Gradio uses a specific API format
        api_url = f"{base_url}/api/predict"
        
        # Check what endpoints are available
        config_response = requests.get(f"{base_url}/config")
        if config_response.status_code == 200:
            print(f"✓ Config endpoint is available")
            config = config_response.json()
            print(f"  App title: {config.get('title', 'N/A')}")
            print(f"  Components: {len(config.get('components', []))} found")
        
        print("\n--- Chat Test ---")
        print("Note: The chat functionality requires indexed GraphRAG data.")
        print("Since the output folder is empty, search queries will fail gracefully.")
        print("To fully test, you need to run the indexing pipeline first:")
        print("  python -m graphrag.index --root .")
        
    except Exception as e:
        print(f"Error testing API: {e}")

if __name__ == "__main__":
    test_gradio_api()
