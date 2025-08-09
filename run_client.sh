#!/bin/bash

# Script para regenerar protobuf files e executar o GameClient
# Autor: GameDev Team
# Data: 2025-08-09

set -e  # Exit on any error

echo "🔧 Starting GameClient setup and execution..."
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -d "src/GameServer/Protos" ]; then
    print_error "Please run this script from the RPG root directory"
    exit 1
fi

print_status "Checking Docker installation..."
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

print_success "Docker found"

# Create Generated directory if it doesn't exist
print_status "Creating Generated directory..."
mkdir -p src/GameClient/Generated

# Step 1: Regenerate protobuf files
print_status "Regenerating protobuf files..."
docker run --rm -v $(pwd):/workspace -w /workspace python:3.11-slim sh -c "
    pip install grpcio-tools==1.60.0 > /dev/null 2>&1 &&
    python -m grpc_tools.protoc \
        --proto_path=src/GameServer/Protos \
        --python_out=src/GameClient/Generated \
        --grpc_python_out=src/GameClient/Generated \
        src/GameServer/Protos/*.proto
" || {
    print_error "Failed to regenerate protobuf files"
    exit 1
}

print_success "Protobuf files regenerated successfully"

# Step 2: Fix imports in generated files
print_status "Fixing imports in generated gRPC files..."

# Fix auth_pb2_grpc.py
if [ -f "src/GameClient/Generated/auth_pb2_grpc.py" ]; then
    sed -i 's/^import auth_pb2 as auth__pb2$/from . import auth_pb2 as auth__pb2/' src/GameClient/Generated/auth_pb2_grpc.py
    print_success "Fixed imports in auth_pb2_grpc.py"
fi

# Fix player_pb2_grpc.py
if [ -f "src/GameClient/Generated/player_pb2_grpc.py" ]; then
    sed -i 's/^import player_pb2 as player__pb2$/from . import player_pb2 as player__pb2/' src/GameClient/Generated/player_pb2_grpc.py
    print_success "Fixed imports in player_pb2_grpc.py"
fi

# Fix world_pb2_grpc.py
if [ -f "src/GameClient/Generated/world_pb2_grpc.py" ]; then
    sed -i 's/^import world_pb2 as world__pb2$/from . import world_pb2 as world__pb2/' src/GameClient/Generated/world_pb2_grpc.py
    print_success "Fixed imports in world_pb2_grpc.py"
fi

# Step 3: Create __init__.py if it doesn't exist
if [ ! -f "src/GameClient/Generated/__init__.py" ]; then
    touch src/GameClient/Generated/__init__.py
    print_status "Created __init__.py in Generated directory"
fi

# Step 4: Verify protobuf files were created
print_status "Verifying generated files..."
required_files=(
    "src/GameClient/Generated/auth_pb2.py"
    "src/GameClient/Generated/auth_pb2_grpc.py"
    "src/GameClient/Generated/player_pb2.py"
    "src/GameClient/Generated/player_pb2_grpc.py"
    "src/GameClient/Generated/world_pb2.py"
    "src/GameClient/Generated/world_pb2_grpc.py"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        print_success "✓ $file"
    else
        print_error "✗ $file (missing)"
        exit 1
    fi
done

# Step 5: Check for LeaveWorldRequest
print_status "Verifying LeaveWorldRequest is available..."
if grep -q "LeaveWorldRequest" src/GameClient/Generated/player_pb2.py; then
    print_success "✓ LeaveWorldRequest found in protobuf"
else
    print_warning "⚠ LeaveWorldRequest not found in protobuf"
fi

# Step 6: Check Python installation
print_status "Checking Python installation..."
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    print_success "Python3 found: $(python3 --version)"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
    print_success "Python found: $(python --version)"
else
    print_error "Python not found. Please install Python 3.8+"
    exit 1
fi

# Step 7: Check required Python packages
print_status "Checking required Python packages..."
cd src/GameClient

if ! $PYTHON_CMD -c "import grpc; import pygame" &> /dev/null; then
    print_warning "Some required packages are missing. Installing..."
    $PYTHON_CMD -m pip install grpcio pygame protobuf || {
        print_error "Failed to install required packages"
        exit 1
    }
    print_success "Required packages installed"
else
    print_success "All required packages are available"
fi

# Step 8: Display connection info
echo ""
echo "=============================================="
print_status "GameClient is ready to launch!"
echo ""
print_status "Connection details:"
echo "  • Server address: localhost:5008 (default)"
echo "  • Use GRPC_PORT environment variable to change port"
echo ""
print_status "Controls:"
echo "  • ARROW KEYS or WASD: Move"
echo "  • SHIFT + movement: Run"
echo "  • F1: Attack"
echo "  • F11: Fullscreen"
echo "  • I: Inventory"
echo "  • C: Character stats"
echo ""

# Step 9: Launch the client
print_status "Launching GameClient..."
echo "=============================================="

# Check if server is running (optional warning)
if ! nc -z localhost 5008 2>/dev/null; then
    print_warning "Server doesn't seem to be running on localhost:5008"
    print_warning "Make sure to start the GameServer before connecting"
    echo ""
fi

# Execute the client
exec $PYTHON_CMD main.py
