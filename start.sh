#!/bin/bash

# Nexus Intelligent Chatbot System - Startup Script
# This script initializes the database and starts all services

set -e

echo "=========================================="
echo "Nexus Intelligent Chatbot System"
echo "Startup Script"
echo "=========================================="
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo "✓ .env file created. Please update it with your configuration."
    echo ""
fi

# Load environment variables
export $(cat .env | grep -v '#' | xargs)

echo "📦 Installing Python dependencies..."
pip install -r requirements.txt
echo "✓ Dependencies installed"
echo ""

echo "🗄️  Initializing database..."
python nexus/init_db.py
echo "✓ Database initialized"
echo ""

echo "🔐 Initializing authentication database..."
python auth/main.py &
AUTH_PID=$!
sleep 5
kill $AUTH_PID 2>/dev/null || true
echo "✓ Authentication service initialized"
echo ""

echo "🚀 Starting Nexus services..."
echo ""
echo "Services will be available at:"
echo "  - Nexus API: http://localhost:8000"
echo "  - Auth Service: http://localhost:8002"
echo "  - RAG Service: http://localhost:8001"
echo ""
echo "API Documentation: http://localhost:8000/docs"
echo ""

# Start the main API server
echo "Starting Nexus API server..."
uvicorn nexus.api:app --host 0.0.0.0 --port 8000 --reload

