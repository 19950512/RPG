#!/bin/bash

# Script de configuração do ambiente de desenvolvimento para RPG Game Server
# Execute este script após clonar o repositório
# Uso: ./setup-dev-environment.sh

set -e  # Para o script em caso de erro

echo "🎮 Configurando ambiente de desenvolvimento para RPG Game Server..."
echo "================================================================="

# Verificar se estamos no diretório correto
if [ ! -f "docker-compose.yml" ] || [ ! -d "src/GameServer" ]; then
    echo "❌ Erro: Execute este script na raiz do repositório RPG"
    echo "   Certifique-se de estar no diretório que contém docker-compose.yml"
    exit 1
fi

# Função para verificar se um comando existe
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Verificar dependências básicas
echo "🔍 Verificando dependências do sistema..."

if ! command_exists python3; then
    echo "❌ Python 3 não encontrado. Instalando..."
    if command_exists apt-get; then
        sudo apt-get update
        sudo apt-get install -y python3 python3-pip python3-venv
    elif command_exists yum; then
        sudo yum install -y python3 python3-pip
    elif command_exists brew; then
        brew install python3
    else
        echo "❌ Não foi possível instalar Python 3. Instale manualmente."
        exit 1
    fi
fi

if ! command_exists docker; then
    echo "❌ Docker não encontrado. Por favor, instale o Docker primeiro:"
    echo "   https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command_exists docker-compose; then
    echo "❌ Docker Compose não encontrado. Por favor, instale o Docker Compose:"
    echo "   https://docs.docker.com/compose/install/"
    exit 1
fi

if ! command_exists git; then
    echo "❌ Git não encontrado. Instalando..."
    if command_exists apt-get; then
        sudo apt-get install -y git
    elif command_exists yum; then
        sudo yum install -y git
    elif command_exists brew; then
        brew install git
    else
        echo "❌ Não foi possível instalar Git. Instale manualmente."
        exit 1
    fi
fi

echo "✅ Dependências do sistema verificadas"

# Criar ambiente virtual Python
echo "🐍 Configurando ambiente virtual Python..."
VENV_DIR="venv"

if [ -d "$VENV_DIR" ]; then
    echo "⚠️  Ambiente virtual já existe. Removendo e recriando..."
    rm -rf "$VENV_DIR"
fi

python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

echo "✅ Ambiente virtual Python criado e ativado"

# Instalar dependências Python
echo "📦 Instalando dependências Python..."
pip install --upgrade pip

# Instalar dependências do cliente
if [ -f "src/GameClient/requirements.txt" ]; then
    pip install -r src/GameClient/requirements.txt
    echo "✅ Dependências do GameClient instaladas"
else
    echo "⚠️  Arquivo requirements.txt não encontrado. Instalando dependências básicas..."
    pip install grpcio grpcio-tools pygame protobuf
fi

# Verificar se .NET está instalado (opcional para desenvolvimento do cliente)
echo "🔧 Verificando .NET SDK (opcional para servidor)..."
if command_exists dotnet; then
    echo "✅ .NET SDK encontrado: $(dotnet --version)"
else
    echo "⚠️  .NET SDK não encontrado. Isso é opcional se você só vai trabalhar com o cliente Python."
    echo "   Para desenvolvimento completo, instale .NET 8.0 SDK:"
    echo "   https://dotnet.microsoft.com/download/dotnet/8.0"
fi

# Configurar arquivos de ambiente
echo "⚙️  Configurando arquivos de ambiente..."
if [ ! -f "dev.env" ]; then
    if [ -f "dev.env.example" ]; then
        cp dev.env.example dev.env
        echo "✅ Arquivo dev.env criado a partir do exemplo"
    else
        echo "⚠️  dev.env.example não encontrado"
    fi
fi

if [ ! -f "test_connection.sh" ]; then
    if [ -f "test_connection.sh.example" ]; then
        cp test_connection.sh.example test_connection.sh
        chmod +x test_connection.sh
        echo "✅ Script de teste criado e tornado executável"
    else
        echo "⚠️  test_connection.sh.example não encontrado"
    fi
fi

# Gerar certificados se necessário
echo "🔐 Verificando certificados..."
if [ ! -f "certs/gameserver.crt" ] || [ ! -f "certs/gameserver.key" ]; then
    if [ -f "scripts/generate-certs.sh" ]; then
        echo "🔑 Gerando certificados SSL..."
        chmod +x scripts/generate-certs.sh
        ./scripts/generate-certs.sh
        echo "✅ Certificados SSL gerados"
    else
        echo "⚠️  Script de geração de certificados não encontrado"
    fi
fi

# Criar script de ativação do ambiente
echo "📝 Criando script de ativação..."
cat > activate-env.sh << 'EOF'
#!/bin/bash
# Script para ativar o ambiente virtual
# Uso: source ./activate-env.sh

if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "🐍 Ambiente virtual Python ativado"
    echo "📁 Para desativar: deactivate"
else
    echo "❌ Ambiente virtual não encontrado. Execute setup-dev-environment.sh primeiro"
fi
EOF
chmod +x activate-env.sh

# Criar script para executar o cliente
echo "🎮 Criando script para executar o cliente..."
cat > run-client.sh << 'EOF'
#!/bin/bash
# Script para executar o cliente do jogo
# Uso: ./run-client.sh

# Ativar ambiente virtual se não estiver ativo
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        echo "🐍 Ambiente virtual ativado"
    else
        echo "❌ Ambiente virtual não encontrado. Execute setup-dev-environment.sh primeiro"
        exit 1
    fi
fi

# Ir para o diretório do cliente
cd src/GameClient

# Verificar se o servidor está rodando
echo "🔍 Verificando se o servidor está rodando..."
if ! docker-compose -f ../../docker-compose.yml ps | grep -q "gameserver.*Up"; then
    echo "⚠️  Servidor não está rodando. Iniciando..."
    cd ../..
    docker-compose up -d
    echo "⏱️  Aguardando servidor inicializar..."
    sleep 5
    cd src/GameClient
fi

echo "🎮 Iniciando cliente do jogo..."
python main.py
EOF
chmod +x run-client.sh

# Criar script para parar todos os serviços
echo "🛑 Criando script para parar serviços..."
cat > stop-all.sh << 'EOF'
#!/bin/bash
# Script para parar todos os serviços Docker
echo "🛑 Parando todos os serviços..."
docker-compose down
echo "✅ Todos os serviços foram parados"
EOF
chmod +x stop-all.sh

# Testar conexão com Docker
echo "🐳 Testando Docker..."
if docker info >/dev/null 2>&1; then
    echo "✅ Docker está funcionando"
else
    echo "❌ Docker não está funcionando. Verifique se o serviço está rodando:"
    echo "   sudo systemctl start docker  # Linux"
    echo "   # ou inicie o Docker Desktop"
fi

# Informações finais
echo ""
echo "🎉 CONFIGURAÇÃO CONCLUÍDA!"
echo "=========================="
echo ""
echo "📋 O que foi configurado:"
echo "   ✅ Ambiente virtual Python em 'venv/'"
echo "   ✅ Dependências Python instaladas"
echo "   ✅ Scripts de desenvolvimento criados"
echo "   ✅ Arquivos de configuração preparados"
echo ""
echo "🚀 Para começar a desenvolver:"
echo "   1. Ative o ambiente virtual:"
echo "      source ./activate-env.sh"
echo ""
echo "   2. Inicie o servidor (primeira vez pode demorar):"
echo "      docker-compose up -d"
echo ""
echo "   3. Execute o cliente:"
echo "      ./run-client.sh"
echo ""
echo "📁 Scripts úteis criados:"
echo "   • ./activate-env.sh     - Ativa o ambiente Python"
echo "   • ./run-client.sh       - Executa o cliente do jogo"
echo "   • ./stop-all.sh         - Para todos os serviços"
echo ""
echo "🐳 Comandos Docker úteis:"
echo "   • docker-compose up -d          - Inicia os serviços"
echo "   • docker-compose down           - Para os serviços"
echo "   • docker-compose logs gameserver - Ver logs do servidor"
echo "   • docker-compose ps             - Status dos serviços"
echo ""
echo "🔧 Desenvolvimento:"
echo "   • Código do servidor: src/GameServer/"
echo "   • Código do cliente:  src/GameClient/"
echo "   • Logs:              logs/"
echo ""
echo "❓ Em caso de problemas:"
echo "   • Verifique os logs: docker-compose logs"
echo "   • Reinicie os serviços: docker-compose restart"
echo "   • Reconstrua as imagens: docker-compose build --no-cache"
echo ""
echo "✨ Ambiente pronto para desenvolvimento!"
