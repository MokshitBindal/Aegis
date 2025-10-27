# aegis-agent/main.py

import argparse
import sys
import platform
import threading
import time
from internal.agent.id import get_agent_id
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
    print(f"Starting agent (ID: {args.agent_id})...")
    
    collector_thread = None
    
    # --- MODIFICATION: Initialize Forwarder ---
    forwarder = Forwarder(storage=args.storage, agent_id=args.agent_id)
    
    if args.os_name == "Linux":
        print("Linux OS detected. Initializing JournaldCollector...")
        try:
            from internal.collector.journald_linux import JournaldCollector
            
            collector = JournaldCollector(storage=args.storage)
            
            collector_thread = threading.Thread(
                target=collector.run, 
                daemon=True
            )
            collector_thread.start()
            print("JournaldCollector thread started.")
            
        except ImportError:
            print("Failed to import JournaldCollector. Is 'systemd-python' installed?")
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
    Placeholder function for agent registration.
    """
    print(f"Registering agent (ID: {args.agent_id}) with token: {args.token}...")
    args.storage.close()


if __name__ == "__main__":
    main()