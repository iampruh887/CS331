#!/bin/bash

# Stop all Nexus services

echo "Stopping all Nexus services..."

if [ -f .pids ]; then
    while read pid; do
        if ps -p $pid > /dev/null 2>&1; then
            echo "Killing process $pid"
            kill $pid 2>/dev/null
        fi
    done < .pids
    rm .pids
fi

# Also kill by port
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:8002 | xargs kill -9 2>/dev/null
lsof -ti:5173 | xargs kill -9 2>/dev/null

echo "All services stopped"
