#!/bin/bash

# Nexus System Startup Script
# This script starts all three required services

echo "=========================================="
echo "Starting Nexus System"
echo "=========================================="

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "WARNING: No virtual environment detected"
    echo "Please activate your virtual environment first:"
    echo "  source venv/bin/activate"
    echo "  or"
    echo "  source cs331env/bin/activate"
    exit 1
fi

# Kill any existing processes on the ports
echo "Cleaning up existing processes..."
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:8002 | xargs kill -9 2>/dev/null
lsof -ti:5173 | xargs kill -9 2>/dev/null

# Wait a moment
sleep 2

# Start Auth Service
echo ""
echo "Starting Auth Service on port 8000..."
python -m uvicorn auth.main:app --host 0.0.0.0 --port 8000 --reload > auth.log 2>&1 &
AUTH_PID=$!
echo "Auth Service PID: $AUTH_PID"

# Wait for auth to start
sleep 3

# Start Nexus API
echo ""
echo "Starting Nexus API on port 8002..."
uvicorn nexus.api:app --host 0.0.0.0 --port 8002 --reload > nexus.log 2>&1 &
NEXUS_PID=$!
echo "Nexus API PID: $NEXUS_PID"

# Wait for nexus to start
sleep 3

# Start Frontend
echo ""
echo "Starting Frontend on port 5173..."
cd client
npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..
echo "Frontend PID: $FRONTEND_PID"

# Wait for frontend to start
sleep 5

echo ""
echo "=========================================="
echo "All services started!"
echo "=========================================="
echo ""
echo "Services:"
echo "  Auth API:    http://localhost:8000"
echo "  Nexus API:   http://localhost:8002"
echo "  Frontend:    http://localhost:5173"
echo ""
echo "Logs:"
echo "  Auth:        tail -f auth.log"
echo "  Nexus:       tail -f nexus.log"
echo "  Frontend:    tail -f frontend.log"
echo ""
echo "To stop all services:"
echo "  kill $AUTH_PID $NEXUS_PID $FRONTEND_PID"
echo ""
echo "Or run: ./stop_all.sh"
echo ""

# Save PIDs to file for stop script
echo "$AUTH_PID" > .pids
echo "$NEXUS_PID" >> .pids
echo "$FRONTEND_PID" >> .pids

# Test services
echo "Testing services..."
sleep 2

if curl -s http://localhost:8000 > /dev/null; then
    echo "✓ Auth Service is running"
else
    echo "✗ Auth Service failed to start - check auth.log"
fi

if curl -s http://localhost:8002/health > /dev/null; then
    echo "✓ Nexus API is running"
else
    echo "✗ Nexus API failed to start - check nexus.log"
fi

if curl -s http://localhost:5173 > /dev/null; then
    echo "✓ Frontend is running"
else
    echo "✗ Frontend failed to start - check frontend.log"
fi

echo ""
echo "Open http://localhost:5173 in your browser"
echo ""
