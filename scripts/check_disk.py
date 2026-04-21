#!/usr/bin/env python3
"""
Check disk space metrics.

This script queries the system for disk usage information and returns
it in a human-readable format.

Requirements: 10.1, 10.2
"""

import sys
import psutil
from datetime import datetime


def check_disk(path="/"):
    """
    Check disk usage for a given path.
    
    Args:
        path (str): Path to check (default: root)
    
    Returns:
        dict: Disk metrics including total, used, free, and percentage
    """
    try:
        # Get disk usage for the path
        disk_usage = psutil.disk_usage(path)
        
        # Get all disk partitions
        partitions = psutil.disk_partitions()
        
        all_disks = []
        for partition in partitions:
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                all_disks.append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "total_bytes": usage.total,
                    "used_bytes": usage.used,
                    "free_bytes": usage.free,
                    "percent": usage.percent
                })
            except (PermissionError, OSError):
                # Skip partitions we can't access
                continue
        
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "root_path": {
                "path": path,
                "total_bytes": disk_usage.total,
                "used_bytes": disk_usage.used,
                "free_bytes": disk_usage.free,
                "percent": disk_usage.percent
            },
            "all_partitions": all_disks,
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
        metrics (dict): Disk metrics
        
    Returns:
        str: Formatted output
    """
    if metrics.get("status") == "error":
        return f"Error checking disk: {metrics.get('error')}"
    
    output = []
    output.append("=== Disk Metrics ===")
    output.append(f"Timestamp: {metrics['timestamp']}")
    
    root = metrics['root_path']
    output.append(f"\nRoot Path ({root['path']}):")
    output.append(f"  Total: {format_bytes(root['total_bytes'])}")
    output.append(f"  Used: {format_bytes(root['used_bytes'])} ({root['percent']}%)")
    output.append(f"  Free: {format_bytes(root['free_bytes'])}")
    
    output.append("\nAll Partitions:")
    for disk in metrics['all_partitions']:
        output.append(f"\n  {disk['device']} ({disk['mountpoint']})")
        output.append(f"    Type: {disk['fstype']}")
        output.append(f"    Total: {format_bytes(disk['total_bytes'])}")
        output.append(f"    Used: {format_bytes(disk['used_bytes'])} ({disk['percent']}%)")
        output.append(f"    Free: {format_bytes(disk['free_bytes'])}")
    
    return "\n".join(output)


if __name__ == "__main__":
    try:
        # Check root path by default, or specified path if provided
        path = sys.argv[1] if len(sys.argv) > 1 else "/"
        metrics = check_disk(path)
        print(format_output(metrics))
        
        # Exit with appropriate code
        sys.exit(0 if metrics.get("status") == "success" else 1)
        
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)
