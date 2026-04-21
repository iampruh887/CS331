#!/bin/bash
#
# Restart a system service.
#
# This script restarts a system service and returns the result.
# This is a WRITE ACTION that modifies system state.
#
# Requirements: 10.1, 10.2
#
# Usage: ./restart_service.sh <service_name>

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
    local action="$2"
    local success="$3"
    local message="$4"
    local timestamp="$5"
    
    echo "=== Service Restart Result ==="
    echo "Timestamp: $timestamp"
    echo "Service: $service"
    echo "Action: $action"
    echo "Success: $success"
    echo "Message: $message"
}

# Get current timestamp
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Check if systemctl is available
if ! command -v systemctl &> /dev/null; then
    format_output "$SERVICE_NAME" "restart" "no" "systemctl not found"
    exit 1
fi

# Check if service exists
if ! systemctl list-unit-files "$SERVICE_NAME.service" &> /dev/null; then
    format_output "$SERVICE_NAME" "restart" "no" "Service not found"
    exit 1
fi

# Attempt to restart the service
if systemctl restart "$SERVICE_NAME" 2>/dev/null; then
    # Verify the service is running
    sleep 1
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        format_output "$SERVICE_NAME" "restart" "yes" "Service restarted successfully"
        exit 0
    else
        format_output "$SERVICE_NAME" "restart" "no" "Service failed to start after restart"
        exit 1
    fi
else
    format_output "$SERVICE_NAME" "restart" "no" "Failed to restart service (may require elevated privileges)"
    exit 1
fi
