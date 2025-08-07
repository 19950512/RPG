#!/bin/bash

# Production deployment script

set -e

echo "🚀 Deploying Game Server to production..."

# Check if certificates exist
if [ ! -f "./certs/gameserver.crt" ] || [ ! -f "./certs/gameserver.key" ]; then
    echo "❌ Production certificates not found!"
    echo "Please place your CA-signed certificates in ./certs/"
    echo "Required files:"
    echo "  - gameserver.crt"
    echo "  - gameserver.key"
    echo "  - gameserver.pfx (for .NET)"
    exit 1
fi

# Create logs directory
mkdir -p ./logs

# Pull latest images and deploy
echo "🐳 Deploying production containers..."
docker-compose up --build -d

echo "⏳ Waiting for services to be ready..."
sleep 15

# Check if services are healthy
echo "🏥 Checking service health..."
docker-compose ps

# Run database migrations
echo "📊 Running database migrations..."
docker-compose exec gameserver dotnet ef database update

echo ""
echo "✅ Game Server production deployment complete!"
echo ""
echo "🔗 Services:"
echo "  - Game Server gRPC: https://localhost:5001"
echo "  - Nginx Load Balancer: https://localhost:443"
echo "  - PostgreSQL: localhost:5432"
echo "  - Redis: localhost:6379"
echo ""
echo "📊 To view logs:"
echo "  docker-compose logs -f gameserver"
echo ""
echo "🔍 To monitor:"
echo "  docker-compose exec postgres psql -U gameuser -d gameserver"
echo "  docker-compose exec redis redis-cli"
