# aegis-server/internal/analysis/rules_config.py

"""
Configuration for correlation rules.
Allows easy tuning of detection thresholds and rule parameters.
"""

from dataclasses import dataclass
from typing import Literal


@dataclass
class RuleConfig:
    """Base configuration for correlation rules"""

    enabled: bool = True
    severity: Literal["low", "medium", "high", "critical"] = "medium"


@dataclass
class SSHBruteForceConfig(RuleConfig):
    """Configuration for SSH brute force detection"""

    name: str = "SSH Failed Login Attempts"
    min_failures: int = 3
    timeframe_minutes: int = 5
    severity: Literal["low", "medium", "high", "critical"] = "high"


@dataclass
class DistributedBruteForceConfig(RuleConfig):
    """Configuration for distributed brute force detection"""

    name: str = "Distributed Brute Force Attack"
    min_devices: int = 2
    min_attempts: int = 5
    timeframe_minutes: int = 5
    severity: Literal["low", "medium", "high", "critical"] = "critical"


@dataclass
class PrivilegeEscalationConfig(RuleConfig):
    """Configuration for privilege escalation detection"""

    name: str = "Privilege Escalation Attempt"
    min_attempts: int = 2
    timeframe_minutes: int = 5
    severity: Literal["low", "medium", "high", "critical"] = "high"


@dataclass
class PortScanConfig(RuleConfig):
    """Configuration for port scan detection"""

    name: str = "Port Scan Detected"
    min_unique_ports: int = 10
    timeframe_minutes: int = 5
    severity: Literal["low", "medium", "high", "critical"] = "high"


@dataclass
class ResourceAnomalyConfig(RuleConfig):
    """Configuration for resource anomaly detection"""

    name: str = "Coordinated Resource Spike"
    min_devices: int = 2
    cpu_threshold: float = 85.0
    memory_threshold: float = 90.0
    min_spike_count: int = 2
    timeframe_minutes: int = 5
    severity: Literal["low", "medium", "high", "critical"] = "medium"


class CorrelationRulesConfig:
    """Master configuration for all correlation rules"""

    def __init__(self):
        self.ssh_brute_force = SSHBruteForceConfig()
        self.distributed_brute_force = DistributedBruteForceConfig()
        self.privilege_escalation = PrivilegeEscalationConfig()
        self.port_scan = PortScanConfig()
        self.resource_anomaly = ResourceAnomalyConfig()

        # Global settings
        self.analysis_interval_seconds = 60
        self.lookback_minutes = 5

    def get_enabled_rules(self) -> list[str]:
        """Returns list of enabled rule names"""
        enabled = []
        for rule_name, rule_config in self.__dict__.items():
            if isinstance(rule_config, RuleConfig) and rule_config.enabled:
                enabled.append(rule_name)
        return enabled


# Global configuration instance
RULES_CONFIG = CorrelationRulesConfig()
