"""Models for system metrics"""
from datetime import datetime
from typing import Dict, Any
from pydantic import BaseModel, Field

class SystemMetrics(BaseModel):
    """System metrics data model"""
    agent_id: str
    timestamp: datetime
    cpu: Dict[str, Any] = Field(
        description="CPU metrics including usage percentage and count"
    )
    memory: Dict[str, Any] = Field(
        description="Memory metrics including usage and swap"
    )
    disk: Dict[str, Any] = Field(
        description="Disk metrics including usage and I/O"
    )
    network: Dict[str, Any] = Field(
        description="Network metrics including bytes sent/received"
    )
    process: Dict[str, Any] = Field(
        description="Process related metrics"
    )