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
SESSION = "ollama_runtime"

def setup_ollama():
    daytona = Daytona(DaytonaConfig())
    
    # Search for existing Ollama sandbox or create new
    sb = None
    for s in daytona.list():
        # Simple check: does it have ollama installed?
        try:
            res = s.process.exec("ollama --version")
            if "ollama" in res.result.lower():
                sb = s
                print(f"Using existing Ollama sandbox: {sb.id}")
                break
        except:
            continue
            
    if not sb:
        print("Creating new CPU Sandbox for Ollama...")
        sb = daytona.create(
            CreateSandboxBaseParams(
                resources=Resources(cpu=4, memory=8),
                auto_stop_interval=0,
                ephemeral=True,
            ),
            timeout=600,
        )
        print(f"Sandbox created: {sb.id}")
        print("Installing Ollama...")
        sb.process.exec("curl -fsSL https://ollama.com/install.sh | sh")
        print("Ollama installed.")

    # Ensure session exists and start server
    print(f"Ensuring session {SESSION} exists and starting server...")
    try:
        sb.process.create_session(SESSION)
    except:
        pass # Session might already exist
        
    #Start serve
    sb.process.execute_session_command(
        SESSION,
        SessionExecuteRequest(
            command="ollama serve",
            run_async=True,
        ),
    )
    
    # Pull model
    print(f"Pulling {MODEL}...")
    sb.process.exec(f"ollama pull {MODEL}")
    
    # Health check
    pv = sb.get_preview_link(PORT)
    hdr = {"x-daytona-preview-token": pv.token}
    
    print(f"Polling {pv.url}...")
    for _ in range(20):
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
        
    raise Exception("Ollama failed to become healthy")

if __name__ == "__main__":
    try:
        setup_ollama()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
