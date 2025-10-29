# aegis-agent/internal/analysis/command_rules.py

"""
Command analysis rules for detecting suspicious shell activity.
"""

import re
from typing import Dict, Optional


# Dangerous command patterns
DANGEROUS_COMMANDS = {
    'data_destruction': [
        r'\brm\s+-rf\s+/',
        r'\bdd\s+if=',
        r'\bmkfs\.',
        r'\bshred\b',
        r':\(\)\{.*:\|:&\};:',  # Fork bomb
    ],
    'privilege_escalation': [
        r'\bsudo\s+',
        r'\bsu\s+',
        r'\bsudo\s+-i',
        r'\bsudo\s+su',
        r'chmod\s+[u+]?s\b',  # SUID bit
    ],
    'network_recon': [
        r'\bnmap\b',
        r'\bnc\s+-l',  # netcat listen
        r'\bnetcat\b',
        r'\bmasscan\b',
        r'\bping\s+-c\s+\d+',
    ],
    'data_exfiltration': [
        r'\bscp\s+.*@\d+\.\d+',  # SCP to external IP
        r'\brsync\s+.*@',
        r'\bcurl\s+.*-F',  # File upload
        r'\bwget\s+.*-O-\s+\|',  # Pipe to command
        r'\bbase64\b.*\|.*curl',  # Encoded upload
    ],
    'reverse_shell': [
        r'bash\s+-i\s+>&\s+/dev/tcp/',
        r'nc.*-e\s+/bin/[bs]h',
        r'python.*socket.*connect',
        r'perl.*Socket.*connect',
        r'/bin/sh.*0>&1',
    ],
    'crypto_mining': [
        r'\bxmrig\b',
        r'\bminerd\b',
        r'\bcpuminer\b',
        r'\bccminer\b',
        r'stratum\+tcp://',
    ],
    'persistence': [
        r'crontab\s+-e',
        r'at\s+now\s+\+',
        r'systemctl\s+(enable|start)',
        r'\.bashrc',
        r'\.bash_profile',
        r'authorized_keys',
    ],
    'credential_access': [
        r'/etc/shadow',
        r'/etc/passwd',
        r'\.ssh/id_rsa',
        r'\.aws/credentials',
        r'\.docker/config\.json',
        r'history\s+-c',  # Clear history
    ],
}

# Suspicious argument patterns
SUSPICIOUS_ARGS = [
    r'--no-check-certificate',  # wget/curl ignore SSL
    r'-k\b',  # curl insecure
    r'--insecure',
    r'/dev/null\s+2>&1',  # Hide errors
    r'&\s*$',  # Background process
]


def check_dangerous_command(command: str) -> Optional[Dict]:
    """
    Check if a command matches dangerous patterns.
    
    Args:
        command: Shell command string
        
    Returns:
        Alert dict if dangerous, None otherwise
    """
    command_lower = command.lower()
    
    for category, patterns in DANGEROUS_COMMANDS.items():
        for pattern in patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return {
                    'rule_name': f'Dangerous Command Detected: {category.replace("_", " ").title()}',
                    'severity': _get_severity_for_category(category),
                    'details': {
                        'command': command,
                        'category': category,
                        'pattern_matched': pattern,
                        'reason': _get_reason_for_category(category),
                    }
                }
    
    return None


def check_suspicious_arguments(command: str) -> Optional[Dict]:
    """
    Check for suspicious command arguments/flags.
    
    Args:
        command: Shell command string
        
    Returns:
        Alert dict if suspicious, None otherwise
    """
    for pattern in SUSPICIOUS_ARGS:
        if re.search(pattern, command):
            return {
                'rule_name': 'Suspicious Command Arguments',
                'severity': 'medium',
                'details': {
                    'command': command,
                    'suspicious_arg': pattern,
                    'reason': 'Command uses potentially malicious arguments',
                }
            }
    
    return None


def check_obfuscation(command: str) -> Optional[Dict]:
    """
    Detect command obfuscation techniques.
    
    Args:
        command: Shell command string
        
    Returns:
        Alert dict if obfuscated, None otherwise
    """
    obfuscation_patterns = [
        r'\\x[0-9a-f]{2}',  # Hex encoding
        r'\$\([^)]{50,}\)',  # Long command substitution
        r'eval\s+',  # eval command
        r'base64\s+-d',  # base64 decode
        r'\${.*:.*:.*}',  # Complex variable expansion
    ]
    
    for pattern in obfuscation_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            return {
                'rule_name': 'Obfuscated Command Detected',
                'severity': 'high',
                'details': {
                    'command': command,
                    'obfuscation_type': pattern,
                    'reason': 'Command uses obfuscation to hide intent',
                }
            }
    
    return None


def check_mass_file_operation(command: str) -> Optional[Dict]:
    """
    Detect commands operating on many files (potential ransomware).
    
    Args:
        command: Shell command string
        
    Returns:
        Alert dict if detected, None otherwise
    """
    patterns = [
        r'find\s+.*-exec\s+.*\{\}',  # find with exec
        r'for.*in.*\*.*do',  # Loop over files
        r'xargs\s+',  # xargs operation
    ]
    
    # Check if modifying files
    file_ops = ['rm', 'mv', 'chmod', 'chown', 'encrypt', 'openssl']
    
    for pattern in patterns:
        if re.search(pattern, command):
            for op in file_ops:
                if op in command.lower():
                    return {
                        'rule_name': 'Mass File Operation Detected',
                        'severity': 'high',
                        'details': {
                            'command': command,
                            'operation': op,
                            'reason': 'Command performs operations on multiple files (potential ransomware)',
                        }
                    }
    
    return None


def _get_severity_for_category(category: str) -> str:
    """Map category to severity level."""
    severity_map = {
        'data_destruction': 'critical',
        'privilege_escalation': 'high',
        'network_recon': 'medium',
        'data_exfiltration': 'critical',
        'reverse_shell': 'critical',
        'crypto_mining': 'high',
        'persistence': 'high',
        'credential_access': 'critical',
    }
    return severity_map.get(category, 'medium')


def _get_reason_for_category(category: str) -> str:
    """Get human-readable reason for each category."""
    reasons = {
        'data_destruction': 'Command can destroy data or system files',
        'privilege_escalation': 'Attempt to gain elevated privileges',
        'network_recon': 'Network reconnaissance or scanning activity',
        'data_exfiltration': 'Potential data theft to external system',
        'reverse_shell': 'Reverse shell or remote access attempt',
        'crypto_mining': 'Unauthorized cryptocurrency mining',
        'persistence': 'Attempt to establish persistence on system',
        'credential_access': 'Accessing credential files or clearing audit trail',
    }
    return reasons.get(category, 'Suspicious command detected')


def analyze_command(command_data: Dict) -> Optional[Dict]:
    """
    Main analysis function - runs all checks on a command.
    
    Args:
        command_data: Command dictionary with user, timestamp, command, etc.
        
    Returns:
        Alert dict if any rule triggers, None otherwise
    """
    command = command_data.get('command', '')
    
    if not command:
        return None
    
    # Run all checks
    checks = [
        check_dangerous_command,
        check_suspicious_arguments,
        check_obfuscation,
        check_mass_file_operation,
    ]
    
    for check_func in checks:
        alert = check_func(command)
        if alert:
            # Add command metadata to alert
            alert['details'].update({
                'user': command_data.get('user'),
                'timestamp': command_data.get('timestamp'),
                'shell': command_data.get('shell'),
                'working_directory': command_data.get('working_directory'),
            })
            return alert
    
    return None
