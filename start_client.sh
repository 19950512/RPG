#!/bin/bash

# Script simples para executar apenas o GameClient
# Use este script quando os protobuf files já estão atualizados

set -e

echo "🎮 Starting GameClient..."

# Check if we're in the right directory
if [ ! -d "src/GameClient" ]; then
    echo "❌ Please run this script from the RPG root directory"
    exit 1
fi

# Determine Python command
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Python not found. Please install Python 3.8+"
    exit 1
fi

cd src/GameClient

# Check if server is running
if ! nc -z localhost 5008 2>/dev/null; then
    echo "⚠️  Server doesn't seem to be running on localhost:5008"
    echo "⚠️  Make sure to start the GameServer first"
    echo ""
fi

echo "🚀 Launching GameClient with $PYTHON_CMD..."
exec $PYTHON_CMD main.py
