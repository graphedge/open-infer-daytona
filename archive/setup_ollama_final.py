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
    print("Ollama installed.")

    # 2. Start Ollama Server in a background session
    print(f"Starting Ollama server in session '{SESSION}'...")
    try:
        sb.process.create_session(SESSION)
    except:
        pass
        
    # Use execute_session_command for long-running processes
    sb.process.execute_session_command(
        SESSION,
        SessionExecuteRequest(
            command="ollama serve",
            run_async=True,
        ),
    )
    
    # 3. Pull the model (using a separate exec call)
    print(f"Pulling model {MODEL}... (this takes a few minutes)")
    # We wait a moment for the server to actually start before pulling
    time.sleep(10)
    sb.process.exec(f"ollama pull {MODEL}")
    print(f"Model {MODEL} pulled successfully.")

    # 4. Verify accessibility
    pv = sb.get_preview_link(PORT)
    hdr = {"x-daytona-preview-token": pv.token}
    
    print(f"Polling preview URL: {pv.url}...")
    for i in range(30):
        try:
            # Ollama base endpoint
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
        if i % 5 == 0:
            print("Still waiting for Ollama to respond...")
        
    raise Exception("Ollama failed to become accessible via preview URL")

if __name__ == "__main__":
    try:
        setup_ollama()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
