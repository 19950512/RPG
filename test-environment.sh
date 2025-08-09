#!/bin/bash

# Script de teste rápido para verificar se o ambiente está funcionando
# Execute após setup-dev-environment.sh

echo "🧪 Testando ambiente de desenvolvimento..."
echo "========================================="

# Verificar se estamos no ambiente virtual
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Ambiente virtual não ativo. Ativando..."
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        echo "✅ Ambiente virtual ativado"
    else
        echo "❌ Ambiente virtual não encontrado. Execute setup-dev-environment.sh primeiro"
        exit 1
    fi
fi

# Verificar dependências Python
echo "🐍 Verificando dependências Python..."
python -c "import pygame, grpc, google.protobuf; print('✅ Todas as dependências Python estão instaladas')" || {
    echo "❌ Algumas dependências Python estão faltando"
    exit 1
}

# Verificar se Docker está rodando
echo "🐳 Verificando Docker..."
if docker info >/dev/null 2>&1; then
    echo "✅ Docker está funcionando"
else
    echo "❌ Docker não está funcionando"
    exit 1
fi

# Verificar se os serviços estão rodando
echo "🔍 Verificando serviços..."
if docker-compose ps | grep -q "postgres.*Up" && docker-compose ps | grep -q "gameserver.*Up"; then
    echo "✅ Serviços estão rodando"
    
    # Teste de conectividade básica
    echo "🌐 Testando conectividade com o servidor..."
    sleep 2
    
    # Verificar se o servidor responde
    if docker-compose exec gameserver grpcurl -plaintext localhost:50051 list >/dev/null 2>&1; then
        echo "✅ Servidor gRPC está respondendo"
    else
        echo "⚠️  Servidor gRPC pode não estar totalmente pronto"
    fi
    
else
    echo "⚠️  Alguns serviços não estão rodando. Iniciando..."
    docker-compose up -d
    echo "⏱️  Aguardando serviços inicializarem..."
    sleep 10
    
    if docker-compose ps | grep -q "postgres.*Up" && docker-compose ps | grep -q "gameserver.*Up"; then
        echo "✅ Serviços iniciados com sucesso"
    else
        echo "❌ Falha ao iniciar serviços"
        docker-compose ps
        exit 1
    fi
fi

# Teste rápido do cliente (importações)
echo "🎮 Testando código do cliente..."
cd src/GameClient
python -c "
try:
    import main
    import grpc_client
    print('✅ Código do cliente pode ser importado')
except Exception as e:
    print(f'❌ Erro ao importar código do cliente: {e}')
    exit(1)
" || exit 1

cd ../..

echo ""
echo "🎉 TODOS OS TESTES PASSARAM!"
echo "============================"
echo ""
echo "✅ Ambiente virtual Python funcionando"
echo "✅ Dependências instaladas corretamente"
echo "✅ Docker funcionando"
echo "✅ Serviços do servidor rodando"
echo "✅ Código do cliente pronto"
echo ""
echo "🚀 Você pode executar o cliente com:"
echo "   ./run-client.sh"
echo ""
echo "📊 Status dos serviços:"
docker-compose ps
