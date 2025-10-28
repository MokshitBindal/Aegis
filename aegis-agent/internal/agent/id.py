# aegis-agent/internal/agent/id.py

import uuid
from pathlib import Path

# Per our discussion, we'll use a local file for dev.
# In Phase 4, we'll change this to /etc/aegis-agent/agent_id
AGENT_ID_FILE = Path("agent.id")

def get_agent_id() -> str:
    """
    Retrieves the persistent, unique agent ID.
    
    If the ID file (agent.id) does not exist, it generates a new
    UUID v4, saves it to the file, and returns it.
    
    If the file does exist, it reads the ID from the file and returns it.
    
    Returns:
        str: The agent's unique ID (UUID).
    """
    if AGENT_ID_FILE.exists():
        # File exists, read the ID
        print("Agent ID found, reading from file...")
        agent_id = AGENT_ID_FILE.read_text().strip()
        if not agent_id:
            # Handle case where file is empty
            return _generate_new_id()
        return agent_id
    else:
        # File does not exist, generate a new ID
        return _generate_new_id()

def _generate_new_id() -> str:
    """
    Generates a new UUID, writes it to the file, and returns it.
    """
    print("Generating new agent ID...")
    new_id = str(uuid.uuid4())
    try:
        # We create the file and write the ID
        AGENT_ID_FILE.write_text(new_id)
    except OSError as e:
        print(f"CRITICAL ERROR: Could not write agent ID to file: {e}")
        # In a real scenario, we might want to exit here
        # For now, we'll just return the new_id
    return new_id