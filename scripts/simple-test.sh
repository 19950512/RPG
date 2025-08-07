#!/bin/bash

echo "🧪 Testando servidor GameServer..."
echo "=================================="

# Teste 1: Health Check
echo "1️⃣ Testando Health Check..."
HEALTH_RESPONSE=$(curl -s http://localhost:5002/health)
if [ "$HEALTH_RESPONSE" = "Healthy" ]; then
    echo "✅ Health check passou: $HEALTH_RESPONSE"
else
    echo "❌ Health check falhou: $HEALTH_RESPONSE"
    exit 1
fi

# Teste 2: Verificar se as portas estão abertas
echo ""
echo "2️⃣ Verificando portas abertas..."
if netstat -tulnp | grep -q ":5001.*LISTEN"; then
    echo "✅ Porta 5001 (gRPC) está aberta"
else
    echo "❌ Porta 5001 (gRPC) não está aberta"
fi

if netstat -tulnp | grep -q ":5002.*LISTEN"; then
    echo "✅ Porta 5002 (Health) está aberta"
else
    echo "❌ Porta 5002 (Health) não está aberta"
fi

# Teste 3: Status dos containers
echo ""
echo "3️⃣ Status dos containers..."
docker-compose -f docker-compose.dev.yml ps

echo ""
echo "✅ Servidor está rodando e saudável!"
echo "   - gRPC: localhost:5001"
echo "   - Health: localhost:5002"
echo ""
echo "Para testar com um cliente Python, execute:"
echo "   cd src/GameClient && python main.py"
