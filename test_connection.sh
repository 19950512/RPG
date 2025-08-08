#!/bin/bash

echo "🔗 Testando conexão e sincronização com o servidor via gRPC..."

# Teste usando grpcurl (que deveria estar no container)
echo ""
echo "1. Tentando conectar ao servidor gRPC..."
docker exec gameserver grpcurl -plaintext localhost:5008 list || echo "❌ Não foi possível conectar via grpcurl"

echo ""
echo "2. Verificando se o servidor está respondendo..."
curl -s -I http://localhost:5009/health | head -1 || echo "❌ Servidor HTTP não está respondendo"

echo ""
echo "3. Verificando dados atuais no banco..."
docker-compose exec postgres psql -U gameuser -d gameserver -c "SELECT \"Name\", \"Level\", \"Experience\", \"PositionX\", \"PositionY\", \"IsOnline\", \"LastUpdate\" FROM \"Players\" ORDER BY \"LastUpdate\" DESC LIMIT 5;"

echo ""
echo "🎯 Para testar a sincronização, você precisa:"
echo "   1. Rodar o cliente do jogo (python main.py)"
echo "   2. Fazer login e entrar no mundo"
echo "   3. Mover o personagem ou usar a tecla X para ganhar XP"
echo "   4. As informações devem ser salvas automaticamente a cada 5 segundos"
echo ""
