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

# --- Configuration ---
MODEL = "gemma4:4b"
PORT = 11434
SESSION = "ollama"
BOOT_TIMEOUT = 600

def serve_ollama():
    # Initialize Daytona client
    daytona = Daytona(DaytonaConfig())
    
    print("Creating CPU Sandbox (4vCPU, 8GB RAM)...")
    # Create a CPU sandbox
    sb = daytona.create(
        CreateSandboxBaseParams(
            resources=Resources(
                cpu=4,
                memory=8,
            ),
            auto_stop_interval=0,
            ephemeral=True,
        ),
        timeout=600,
    )
    
    print(f"Sandbox created: {sb.id}")

    # 1. Install Ollama
    print("Installing Ollama...")
    install_cmd = "curl -fsSL https://ollama.com/install.sh | sh"
    sb.process.exec(install_cmd)
    print("Ollama installed successfully.")

    # 2. Start Ollama serve in background
    print("Starting Ollama server in background session...")
    sb.process.create_session(SESSION)
    serve_cmd = sb.process.execute_session_command(
        SESSION,
        SessionExecuteRequest(
            command="ollama serve",
            run_async=True,
        ),
    )
    cmd_id = serve_cmd.cmd_id

    # 3. Pull the model
    print(f"Pulling model {MODEL} (this may take a few minutes)...")
    # We use exec for the pull so it blocks until done
    sb.process.exec(f"ollama pull {MODEL}")
    print(f"Model {MODEL} pulled successfully.")

    # 4. Health check via Preview Link
    pv = sb.get_preview_link(PORT)
    hdr = {"x-daytona-preview-token": pv.token}
    
    deadline = time.time() + BOOT_TIMEOUT
    ready = False
    
    print(f"Waiting for Ollama to respond at {pv.url}...")

    while time.time() < deadline:
        try:
            # Ollama's base endpoint returns "Ollama is running"
            resp = requests.get(pv.url, headers=hdr, timeout=10)
            if resp.status_code == 200:
                ready = True
                break
        except requests.RequestException:
            pass
            
        time.sleep(5)

    if not ready:
        print("Timeout waiting for Ollama to become healthy.")
        sys.exit(1)

    print("\n--- OLLAMA SERVER READY ---")
    print(f"export OLLAMA_ENDPOINT={pv.url}")
    print(f"export OLLAMA_TOKEN={pv.token}")
    print(f"sandbox_id: {sb.id}")
    print("---------------------------")
    
    with open("ollama_info.txt", "w") as f:
        f.write(f"OLLAMA_ENDPOINT={pv.url}\n")
        f.write(f"OLLAMA_TOKEN={pv.token}\n")
        f.write(f"SANDBOX_ID={sb.id}\n")
    
    print("Information saved to ollama_info.txt. Exiting management script.")

if __name__ == "__main__":
    try:
        serve_ollama()
    except KeyboardInterrupt:
        print("\nManagement script stopped.")
