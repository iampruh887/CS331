#!/bin/bash
# Setup script for RAG-enhanced parsing engine

echo "=== RAG-Enhanced Parsing Engine Setup ==="
echo ""

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "❌ Ollama not found. Please install from https://ollama.ai"
    exit 1
fi
echo "✓ Ollama found"

# Check if phi4-mini is available
if ! ollama list | grep -q "phi4-mini"; then
    echo "⚠ Phi4-mini not found. Pulling model..."
    ollama pull phi4-mini
else
    echo "✓ Phi4-mini model available"
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment exists"
fi

# Activate virtual environment
source .venv/bin/activate

# Install requirements
echo "Installing Python dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✓ Dependencies installed"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi

# Check docs folder
if [ -d "docs" ] && [ "$(ls -A docs)" ]; then
    DOC_COUNT=$(find docs -type f \( -name "*.txt" -o -name "*.md" -o -name "*.json" -o -name "*.csv" \) | wc -l)
    echo "✓ Found $DOC_COUNT documents in docs/ folder"
else
    echo "⚠ docs/ folder is empty - RAG will be disabled"
    echo "  Add documents to docs/ to enable knowledge base search"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Usage:"
echo "  source .venv/bin/activate  # Activate environment"
echo "  python main.py             # Interactive mode"
echo "  python main.py 'query'     # Single query"
echo ""
echo "Add documents to docs/ folder to enable RAG capabilities"
