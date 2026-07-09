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
)

load_dotenv()

MODEL = "gemma4:4b"
PORT = 11434

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
    
    # 2. Start Ollama using a nohup background process to ensure it survives the exec call
    print("Starting Ollama server in background...")
    # We use a shell script to start serve and wait for it to be ready locally
    setup_script = f"""
    nohup ollama serve > ollama.log 2>&1 &
    echo "Waiting for Ollama to start..."
    until curl -s localhost:{PORT}/api/tags > /dev/null; do
      sleep 2
    done
    echo "Ollama is up!"
    ollama pull {MODEL}
    """
    sb.process.exec(setup_script)
    print(f"Model {MODEL} pulled and server verified locally.")

    # 3. Verify via Preview Link
    pv = sb.get_preview_link(PORT)
    hdr = {"x-daytona-preview-token": pv.token}
    
    print(f"Polling preview URL: {pv.url}...")
    for _ in range(30):
        try:
            if requests.get(pv.url, headers=hdr, timeout=5).status_code == 200:
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
        
    raise Exception("Ollama failed to become accessible via preview URL")

if __name__ == "__main__":
    try:
        setup_ollama()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
