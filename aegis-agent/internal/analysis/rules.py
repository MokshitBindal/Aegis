# aegis-agent/internal/analysis/rules.py

def check_failed_ssh(log_message: str) -> bool:
    """
    Checks if a log message indicates a failed SSH login attempt.
    
    Args:
        log_message (str): The log message string.
        
    Returns:
        bool: True if it matches the rule, False otherwise.
    """
    # This is a common pattern for failed SSH logins in journald/syslog
    if "Failed password for" in log_message:
        return True
    lower_msg = log_message.lower()
    if "authentication failure" in lower_msg and "sshd" in lower_msg:
        return True
        
    return False

# --- We can add more rule functions here later ---
# def check_sudo_failure(log_message: str) -> bool:
#     ...