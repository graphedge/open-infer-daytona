import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_ollama():
    try:
        with open("ollama_info.txt", "r") as f:
            info = dict(line.strip().split("=") for line in f)
        
        endpoint = info["OLLAMA_ENDPOINT"]
        token = info["OLLAMA_TOKEN"]
        
        print(f"Testing Ollama at {endpoint}...")
        
        # Test the base health endpoint
        hdr = {"x-daytona-preview-token": token}
        resp = requests.get(endpoint, headers=hdr, timeout=10)
        
        if resp.status_code == 200:
            print("Ollama is responding!")
            
            # Test a simple chat completion
            chat_url = f"{endpoint}/api/chat"
            payload = {
                "model": "gemma4:4b",
                "messages": [{"role": "user", "content": "Say hello!"}],
                "stream": False
            }
            
            resp = requests.post(chat_url, json=payload, headers=hdr, timeout=30)
            if resp.status_code == 200:
                print(f"Model Response: {resp.json()['message']['content']}")
            else:
                print(f"Chat call failed: {resp.status_code} {resp.text}")
        else:
            print(f"Health check failed: {resp.status_code}")
            
    except Exception as e:
        print(f"Error testing Ollama: {e}")

if __name__ == "__main__":
    test_ollama()
