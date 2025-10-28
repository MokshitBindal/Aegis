# aegis-agent/main.py

import argparse
import sys
import platform
try:
    import distro
except ImportError:
    distro = None
import threading
import time
import os
import json
import requests
from internal.agent.id import get_agent_id
from internal.agent.credentials import store_credentials, load_credentials, is_registered
from internal.storage.sqlite import Storage
from internal.forwarder.forwarder import Forwarder # <--- IMPORT FORWARDER

def main():
    # ... (no changes to main()) ...
    """
    Main entrypoint for the Aegis Agent.
    Parses command-line arguments and starts the appropriate agent action.
    """
    # --- This is where we load core components ---
    agent_id = get_agent_id()
    os_name = platform.system()
    os_release = platform.release()
    
    print("Aegis SIEM Agent")
    print("--------------------")
    print(f"Agent ID: {agent_id}")
    print(f"Python Version: {sys.version.split()[0]}")
    print(f"Operating System: {os_name} ({os_release})")
    print("--------------------")
    
    try:
        storage = Storage()
    except Exception as e:
        print(f"CRITICAL: Failed to initialize local storage: {e}")
        sys.exit(1)
    
    # Set up the main argument parser
    parser = argparse.ArgumentParser(description="Aegis SIEM Agent")
    subparsers = parser.add_subparsers(dest="command", required=True,
                                       help="Available commands")

    # --- 'run' command ---
    run_parser = subparsers.add_parser("run", help="Run the agent service")
    run_parser.set_defaults(func=run_agent)

    # --- 'register' command ---
    reg_parser = subparsers.add_parser("register", help="Register the agent with the server")
    reg_parser.add_argument("--token", required=True, help="Registration invitation token")
    reg_parser.set_defaults(func=register_agent)

    # Parse the arguments
    args = parser.parse_args()
    
    args.agent_id = agent_id
    args.os_name = os_name
    args.storage = storage

    args.func(args)


def run_agent(args):
    """
    Starts the main agent operations: log collection and forwarding.
    """
    # Ensure the agent is registered before running
    if not is_registered():
        print("ERROR: Agent not registered. Please run the 'register' command first.")
        args.storage.close()
        sys.exit(1)

    print(f"Starting agent (ID: {args.agent_id})...")
    
    collector_thread = None
    
    # --- MODIFICATION: Initialize Forwarder ---
    forwarder = Forwarder(storage=args.storage, agent_id=args.agent_id)
    
    collector = None
    if args.os_name == "Linux":
        distro_name = distro.id() if distro else "unknown"
        print(f"Linux OS detected. Distribution: {distro_name}")
        try:
            from internal.collector.journald_linux import JournaldCollector
            collector = JournaldCollector(storage=args.storage)
        except ImportError:
            print("Failed to import JournaldCollector. Is 'systemd-python' installed?")
            args.storage.close()
            sys.exit(1)
        except Exception as e:
            print(f"Failed to start collector: {e}")
            args.storage.close()
            sys.exit(1)
    elif args.os_name == "Windows":
        print("Windows OS detected. Initializing WindowsEventCollector...")
        try:
            from internal.collector.windows_event import WindowsEventCollector
            collector = WindowsEventCollector(storage=args.storage)
        except ImportError:
            print("Failed to import WindowsEventCollector. Is 'pywin32' installed?")
            args.storage.close()
            sys.exit(1)
        except Exception as e:
            print(f"Failed to start collector: {e}")
            args.storage.close()
            sys.exit(1)
    elif args.os_name == "Darwin":
        print("MacOS detected. Initializing MacUnifiedLogCollector...")
        try:
            from internal.collector.mac_unified import MacUnifiedLogCollector
            collector = MacUnifiedLogCollector(storage=args.storage)
        except ImportError:
            print("Failed to import MacUnifiedLogCollector.")
            args.storage.close()
            sys.exit(1)
        except Exception as e:
            print(f"Failed to start collector: {e}")
            args.storage.close()
            sys.exit(1)
    else:
        print(f"OS '{args.os_name}' not supported for log collection yet.")
        args.storage.close()
        sys.exit(0)

    if collector:
        collector_thread = threading.Thread(
            target=collector.run,
            daemon=True
        )
        collector_thread.start()
        print(f"{collector.__class__.__name__} thread started.")

    # --- MODIFICATION: Start Forwarder ---
    forwarder.start()

    # --- Keep main thread alive ---
    print("Agent is running. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print("\nShutdown signal received. Stopping agent...")
        
    finally:
        # --- MODIFICATION: Stop Forwarder cleanly ---
        forwarder.stop()
        args.storage.close()
        print("Agent stopped.")


def register_agent(args):
    """
    Registers the agent with the server using an invitation token.
    Stores the server URL and agent_id securely on success.
    """
    print(f"Registering agent (ID: {args.agent_id}) with token: {args.token}...")

    # Allow overriding server URL via env
    server_url = os.getenv("AEGIS_SERVER_URL", "http://localhost:8000")
    register_url = f"{server_url}/api/device/register"

    payload = {
        "token": args.token,
        "agent_id": str(args.agent_id),
        "hostname": platform.node(),
        "name": f"agent-{str(args.agent_id)[:8]}"
    }

    try:
        resp = requests.post(register_url, json=payload, timeout=10)
    except requests.RequestException as e:
        print(f"Failed to contact server: {e}")
        args.storage.close()
        return

    if resp.status_code == 201 or (resp.status_code == 400 and "already registered" in resp.text):
        # Handle both new registration and already registered cases
        print("Agent registered successfully with server.")
        try:
            store_credentials(server_url, str(args.agent_id))
            print("Stored credentials securely.")
        except Exception as e:
            print(f"Warning: failed to store credentials securely: {e}")
    else:
        try:
            body = resp.json()
            print(f"Registration failed: {body.get('detail', resp.text)}")
        except Exception:
            print(f"Registration failed: {resp.status_code} {resp.text}")

    args.storage.close()


if __name__ == "__main__":
    main()