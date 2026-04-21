#!/bin/bash

# Test if all services are working

echo "Testing Nexus Services..."
echo ""

# Test Auth Service
echo "1. Testing Auth Service (http://localhost:8000)..."
AUTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000)
if [ "$AUTH_RESPONSE" = "200" ]; then
    echo "   ✓ Auth Service is UP"
    curl -s http://localhost:8000 | python -m json.tool 2>/dev/null || echo "   Response received"
else
    echo "   ✗ Auth Service is DOWN (HTTP $AUTH_RESPONSE)"
    echo "   Try: python -m uvicorn auth.main:app --host 0.0.0.0 --port 8000"
fi

echo ""

# Test Nexus API
echo "2. Testing Nexus API (http://localhost:8002/health)..."
NEXUS_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8002/health)
if [ "$NEXUS_RESPONSE" = "200" ]; then
    echo "   ✓ Nexus API is UP"
    curl -s http://localhost:8002/health | python -m json.tool 2>/dev/null || echo "   Response received"
else
    echo "   ✗ Nexus API is DOWN (HTTP $NEXUS_RESPONSE)"
    echo "   Try: uvicorn nexus.api:app --host 0.0.0.0 --port 8002"
fi

echo ""

# Test Frontend
echo "3. Testing Frontend (http://localhost:5173)..."
FRONTEND_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5173)
if [ "$FRONTEND_RESPONSE" = "200" ]; then
    echo "   ✓ Frontend is UP"
else
    echo "   ✗ Frontend is DOWN (HTTP $FRONTEND_RESPONSE)"
    echo "   Try: cd client && npm run dev"
fi

echo ""

# Test Auth Registration
echo "4. Testing Auth Registration..."
REG_RESPONSE=$(curl -s -X POST http://localhost:8000/register \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"testpass123"}' \
    -w "\nHTTP_CODE:%{http_code}")

HTTP_CODE=$(echo "$REG_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$REG_RESPONSE" | grep -v "HTTP_CODE")

if [ "$HTTP_CODE" = "201" ] || [ "$HTTP_CODE" = "400" ]; then
    echo "   ✓ Auth Registration endpoint is working"
    echo "   Response: $BODY"
else
    echo "   ✗ Auth Registration failed (HTTP $HTTP_CODE)"
    echo "   Response: $BODY"
fi

echo ""
echo "=========================================="
echo "Summary:"
echo "  Auth:     http://localhost:8000"
echo "  Nexus:    http://localhost:8002"
echo "  Frontend: http://localhost:5173"
echo "=========================================="
