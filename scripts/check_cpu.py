#!/usr/bin/env python3
"""
Check CPU usage metrics.

This script queries the system for CPU usage information and returns
it in a human-readable format.

Requirements: 10.1, 10.2
"""

import json
import sys
import psutil
from datetime import datetime


def check_cpu():
    """
    Check CPU usage and return formatted metrics.
    
    Returns:
        dict: CPU metrics including usage percentage and per-core data
    """
    try:
        # Get overall CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Get per-core CPU usage
        per_core = psutil.cpu_percent(interval=1, percpu=True)
        
        # Get CPU count
        cpu_count = psutil.cpu_count(logical=False)
        logical_count = psutil.cpu_count(logical=True)
        
        # Get CPU frequency
        cpu_freq = psutil.cpu_freq()
        
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_usage_percent": cpu_percent,
            "per_core_usage": per_core,
            "physical_cores": cpu_count,
            "logical_cores": logical_count,
            "frequency_mhz": cpu_freq.current if cpu_freq else None,
            "status": "success"
        }
        
        return metrics
        
    except Exception as e:
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "error",
            "error": str(e)
        }


def format_output(metrics):
    """
    Format metrics for human-readable output.
    
    Args:
        metrics (dict): CPU metrics
        
    Returns:
        str: Formatted output
    """
    if metrics.get("status") == "error":
        return f"Error checking CPU: {metrics.get('error')}"
    
    output = []
    output.append("=== CPU Metrics ===")
    output.append(f"Timestamp: {metrics['timestamp']}")
    output.append(f"Overall CPU Usage: {metrics['overall_usage_percent']}%")
    output.append(f"Physical Cores: {metrics['physical_cores']}")
    output.append(f"Logical Cores: {metrics['logical_cores']}")
    
    if metrics['frequency_mhz']:
        output.append(f"CPU Frequency: {metrics['frequency_mhz']:.2f} MHz")
    
    output.append("\nPer-Core Usage:")
    for i, usage in enumerate(metrics['per_core_usage']):
        output.append(f"  Core {i}: {usage}%")
    
    return "\n".join(output)


if __name__ == "__main__":
    try:
        metrics = check_cpu()
        print(format_output(metrics))
        
        # Exit with appropriate code
        sys.exit(0 if metrics.get("status") == "success" else 1)
        
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)
