import os
import sys
import time
import requests
from dotenv import load_dotenv
from daytona import (
    CreateSandboxBaseParams,
    Daytona,
    DaytonaConfig,
    Resources,
    SessionExecuteRequest,
)

load_dotenv()

MODEL = "gemma4:4b"
PORT = 11434
SESSION = "ollama-server"

def setup_ollama():
    daytona = Daytona(DaytonaConfig())
    
    print("Creating fresh CPU Sandbox (4vCPU, 8GB RAM)...")
    sb = daytona.create(
        CreateSandboxBaseParams(
            resources=Resources(cpu=4, memory=8),
            auto_stop_interval=0,
            ephemeral=True,
        ),
        timeout=600,
    )
    print(f"Sandbox created: {sb.id}")

    # 1. Install Ollama
    print("Installing Ollama...")
    sb.process.exec("curl -fsSL https://ollama.com/install.sh | sh")
    
    # 2. Start Ollama Server in a background session with logging
    print(f"Starting Ollama server in session '{SESSION}'...")
    try:
        sb.process.create_session(SESSION)
    except:
        pass
        
    # We use nohup and redirect to a file to ensure we can debug it
    # We wrap it in a a shell that ensures the process is detached
    cmd_str = f"nohup ollama serve > /tmp/ollama.log 2>&1 &"
    sb.process.execute_session_command(
        SESSION,
        SessionExecuteRequest(
            command=cmd_str,
            run_async=True,
        ),
    )
    
    # 3. Pull the model
    print(f"Waiting for server to boot before pulling {MODEL}...")
    time.sleep(15)
    
    # We use exec for the pull. Since we started serve with nohup, it should be available.
    try:
        print(f"Pulling model {MODEL}...")
        sb.process.exec(f"ollama pull {MODEL}")
        print(f"Model {MODEL} pulled successfully.")
    except Exception as e:
        print(f"Pull failed: {e}. Checking logs...")
        print(sb.process.exec("cat /tmp/ollama.log").result)
        sys.exit(1)

    # 4. Verify accessibility via Preview Link
    pv = sb.get_preview_link(PORT)
    hdr = {"x-daytona-preview-token": pv.token}
    
    print(f"Polling preview URL: {pv.url}...")
    for i in range(30):
        try:
            # Check health endpoint
            resp = requests.get(pv.url, headers=hdr, timeout=5)
            if resp.status_code == 200:
                print("\n--- OLLAMA READY ---")
                print(f"Endpoint: {pv.url}")
                print(f"Token: {pv.token}")
                print(f"Sandbox ID: {sb.id}")
                
                with open("ollama_info.txt", "w") as f:
                    f.write(f"OLLAMA_ENDPOINT={pv.url}\n")
                    f.write(f"OLLAMA_TOKEN={pv.token}\n")
                    f.write(f"SANDBOX_ID={sb.id}\n")
                return pv.url, pv.token
        except:
            pass
        time.sleep(5)
        if i % 5 == 0:
            print("Still waiting for Ollama to respond...")
        
    # Final attempt: check logs if still not healthy
    print("Polling failed. Checking logs...")
    print(sb.process.exec("cat /tmp/ollama.log").result)
    raise Exception("Ollama failed to become accessible via preview URL")

if __name__ == "__main__":
    try:
        setup_ollama()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
