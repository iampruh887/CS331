#!/usr/bin/env python3
"""
Check memory usage metrics.

This script queries the system for memory usage information and returns
it in a human-readable format.

Requirements: 10.1, 10.2
"""

import json
import sys
import psutil
from datetime import datetime


def check_memory():
    """
    Check memory usage and return formatted metrics.
    
    Returns:
        dict: Memory metrics including total, used, available, and swap
    """
    try:
        # Get virtual memory stats
        vm = psutil.virtual_memory()
        
        # Get swap memory stats
        swap = psutil.swap_memory()
        
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "virtual_memory": {
                "total_bytes": vm.total,
                "used_bytes": vm.used,
                "available_bytes": vm.available,
                "percent": vm.percent,
                "active_bytes": vm.active,
                "inactive_bytes": vm.inactive,
                "buffers_bytes": vm.buffers,
                "cached_bytes": vm.cached
            },
            "swap_memory": {
                "total_bytes": swap.total,
                "used_bytes": swap.used,
                "free_bytes": swap.free,
                "percent": swap.percent
            },
            "status": "success"
        }
        
        return metrics
        
    except Exception as e:
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "error",
            "error": str(e)
        }


def format_bytes(bytes_val):
    """
    Convert bytes to human-readable format.
    
    Args:
        bytes_val (int): Number of bytes
        
    Returns:
        str: Formatted string (e.g., "1.5 GB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.2f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.2f} PB"


def format_output(metrics):
    """
    Format metrics for human-readable output.
    
    Args:
        metrics (dict): Memory metrics
        
    Returns:
        str: Formatted output
    """
    if metrics.get("status") == "error":
        return f"Error checking memory: {metrics.get('error')}"
    
    output = []
    output.append("=== Memory Metrics ===")
    output.append(f"Timestamp: {metrics['timestamp']}")
    
    vm = metrics['virtual_memory']
    output.append("\nVirtual Memory:")
    output.append(f"  Total: {format_bytes(vm['total_bytes'])}")
    output.append(f"  Used: {format_bytes(vm['used_bytes'])} ({vm['percent']}%)")
    output.append(f"  Available: {format_bytes(vm['available_bytes'])}")
    output.append(f"  Active: {format_bytes(vm['active_bytes'])}")
    output.append(f"  Cached: {format_bytes(vm['cached_bytes'])}")
    
    swap = metrics['swap_memory']
    output.append("\nSwap Memory:")
    output.append(f"  Total: {format_bytes(swap['total_bytes'])}")
    output.append(f"  Used: {format_bytes(swap['used_bytes'])} ({swap['percent']}%)")
    output.append(f"  Free: {format_bytes(swap['free_bytes'])}")
    
    return "\n".join(output)


if __name__ == "__main__":
    try:
        metrics = check_memory()
        print(format_output(metrics))
        
        # Exit with appropriate code
        sys.exit(0 if metrics.get("status") == "success" else 1)
        
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)
