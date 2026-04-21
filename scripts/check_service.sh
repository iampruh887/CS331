#!/bin/bash
#
# Check service status.
#
# This script checks the status of a system service and returns
# human-readable output about its state.
#
# Requirements: 10.1, 10.2
#
# Usage: ./check_service.sh <service_name>

set -e

SERVICE_NAME="${1:-}"

if [ -z "$SERVICE_NAME" ]; then
    echo "Error: Service name required"
    echo "Usage: $0 <service_name>"
    exit 1
fi

# Function to format output
format_output() {
    local service="$1"
    local status="$2"
    local is_active="$3"
    local is_enabled="$4"
    local timestamp="$5"
    
    echo "=== Service Status ==="
    echo "Timestamp: $timestamp"
    echo "Service: $service"
    echo "Status: $status"
    echo "Active: $is_active"
    echo "Enabled: $is_enabled"
}

# Get current timestamp
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Check if systemctl is available
if ! command -v systemctl &> /dev/null; then
    echo "Error: systemctl not found. This script requires systemd."
    exit 1
fi

# Get service status
if systemctl is-active --quiet "$SERVICE_NAME"; then
    IS_ACTIVE="yes"
else
    IS_ACTIVE="no"
fi

# Get service enabled status
if systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
    IS_ENABLED="yes"
else
    IS_ENABLED="no"
fi

# Get full status
STATUS=$(systemctl show "$SERVICE_NAME" --property=ActiveState --value 2>/dev/null || echo "unknown")

# Format and output
format_output "$SERVICE_NAME" "$STATUS" "$IS_ACTIVE" "$IS_ENABLED" "$TIMESTAMP"

# Exit with appropriate code
if [ "$IS_ACTIVE" = "yes" ]; then
    exit 0
else
    exit 1
fi
