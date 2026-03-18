#!/bin/bash
# Quick Start Script for SDLC Agent
# Run this to get up and running quickly

echo "🚀 SDLC Agent - Quick Start Setup"
echo "=================================="
echo ""

# Check Python
echo "✓ Checking Python..."
if ! command -v python &> /dev/null; then
    echo "❌ Python not found. Please install Python 3.8+"
    exit 1
fi

PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
echo "   Python $PYTHON_VERSION found"
echo ""

# Create virtual environment
echo "✓ Creating virtual environment..."
if [ ! -d "venv" ]; then
    python -m venv venv
    echo "   Virtual environment created"
else
    echo "   Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "✓ Activating virtual environment..."
source venv/Scripts/activate || . venv/bin/activate
echo "   Activated"
echo ""

# Install dependencies
echo "✓ Installing dependencies..."
pip install --quiet -r requirements.txt
echo "   Dependencies installed"
echo ""

# Create .env file
echo "✓ Setting up configuration..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "   Created .env (update with your API keys)"
else
    echo "   .env already exists"
fi
echo ""

# Create output and upload directories
echo "✓ Creating directories..."
mkdir -p output uploads tasks
echo "   Directories created"
echo ""

echo "✅ Setup Complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your API keys"
echo "2. Add tasks to tasks/development_tasks.xlsx"
echo "3. Start task watcher: python task_watcher.py"
echo "4. Or start web interface: python web_app.py"
echo ""
echo "For more info, see README.md or WORKFLOW_GUIDE.md"
