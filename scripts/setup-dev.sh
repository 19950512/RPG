#!/bin/bash

# Development setup script

set -e

echo "🎮 Setting up Game Server development environment..."

# Generate certificates if they don't exist
if [ ! -f "./certs/gameserver.pfx" ]; then
    echo "📜 Generating development certificates..."
    ./scripts/generate-certs.sh
else
    echo "📜 Certificates already exist, skipping generation..."
fi

# Create logs directory
mkdir -p ./logs

# Build and start the development environment
echo "🐳 Stopping any existing containers..."
docker-compose -f docker-compose.dev.yml down -v

echo "🐳 Building and starting Docker containers..."
docker-compose -f docker-compose.dev.yml up --build -d

echo "⏳ Waiting for services to be ready..."
sleep 15

# Check if services are healthy
echo "🏥 Checking service health..."
docker-compose -f docker-compose.dev.yml ps

# Test database connection
echo "🗃️ Testing database connection..."
sleep 5
if docker-compose -f docker-compose.dev.yml exec -T postgres psql -U gameuser -d gameserver -c "SELECT COUNT(*) FROM \"Accounts\";" >/dev/null 2>&1; then
    echo "✅ Database tables created successfully!"
else
    echo "⚠️ Database tables not found. Checking initialization..."
    docker-compose -f docker-compose.dev.yml logs postgres | tail -10
fi

echo ""
echo "✅ Game Server development environment is ready!"
echo ""
echo "🔗 Services:"
echo "  - Game Server gRPC: https://localhost:5001"
echo "  - PostgreSQL: localhost:5432"
echo "  - Database: gameserver"
echo "  - Username: gameuser"
echo "  - Password: gamepass123"
echo ""
echo "📚 To test the API, you can use a gRPC client like grpcurl:"
echo "  grpcurl -insecure -d '{\"email\":\"test@example.com\",\"password\":\"password123\"}' localhost:5001 auth.AuthService/CreateAccount"
echo ""
echo "📊 To view logs:"
echo "  docker-compose -f docker-compose.dev.yml logs -f gameserver"
echo ""
echo "🛑 To stop the environment:"
echo "  docker-compose -f docker-compose.dev.yml down"
