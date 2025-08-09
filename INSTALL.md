# Guia de Instalação por Sistema Operacional

## 🐧 Linux (Ubuntu/Debian)

```bash
# 1. Instalar dependências
sudo apt update
sudo apt install -y git python3 python3-pip python3-venv docker.io docker-compose

# 2. Configurar Docker (opcional, pode pedir senha)
sudo usermod -aG docker $USER
# Faça logout e login novamente para aplicar as permissões

# 3. Clonar e configurar
git clone https://github.com/19950512/RPG.git
cd RPG
./setup-dev-environment.sh
```

## 🍎 macOS

```bash
# 1. Instalar Homebrew (se não tiver)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Instalar dependências
brew install git python3 docker docker-compose

# 3. Iniciar Docker Desktop
# Baixe e instale Docker Desktop de: https://www.docker.com/products/docker-desktop

# 4. Clonar e configurar
git clone https://github.com/19950512/RPG.git
cd RPG
./setup-dev-environment.sh
```

## 🪟 Windows

### Opção 1: WSL2 (Recomendado)

```bash
# 1. Instalar WSL2 e Ubuntu
wsl --install

# 2. Dentro do WSL2, seguir as instruções do Linux:
sudo apt update
sudo apt install -y git python3 python3-pip python3-venv docker.io docker-compose

# 3. Configurar Docker Desktop para WSL2
# Download: https://www.docker.com/products/docker-desktop

# 4. Clonar e configurar
git clone https://github.com/19950512/RPG.git
cd RPG
./setup-dev-environment.sh
```

### Opção 2: Windows Nativo

```powershell
# 1. Instalar Python
# Download: https://www.python.org/downloads/

# 2. Instalar Git
# Download: https://git-scm.com/download/win

# 3. Instalar Docker Desktop
# Download: https://www.docker.com/products/docker-desktop

# 4. No PowerShell ou Git Bash:
git clone https://github.com/19950512/RPG.git
cd RPG

# 5. Executar setup manualmente (Windows)
python -m venv venv
venv\Scripts\activate
pip install -r src/GameClient/requirements.txt
```

## 🔧 Solução de Problemas Comuns

### Docker não inicia
```bash
# Linux
sudo systemctl start docker
sudo systemctl enable docker

# macOS/Windows
# Inicie o Docker Desktop manualmente
```

### Permissões do Docker (Linux)
```bash
sudo usermod -aG docker $USER
# Faça logout e login novamente
```

### Python não encontrado
```bash
# Ubuntu/Debian
sudo apt install python3 python3-pip

# CentOS/RHEL
sudo yum install python3 python3-pip

# macOS
brew install python3
```

### Erro de certificados SSL
```bash
# Regenerar certificados
rm -rf certs/*.key certs/*.crt certs/*.pfx
./scripts/generate-certs.sh
```

### Porta já em uso
```bash
# Verificar o que está usando a porta 50051
sudo netstat -tulpn | grep 50051

# Parar todos os containers
docker-compose down

# Reiniciar
docker-compose up -d
```

## 🆘 Obtendo Ajuda

Se você encontrar problemas:

1. **Verifique os logs:**
   ```bash
   docker-compose logs gameserver
   ```

2. **Teste o ambiente:**
   ```bash
   ./test-environment.sh
   ```

3. **Reinicie tudo:**
   ```bash
   ./stop-all.sh
   docker-compose build --no-cache
   docker-compose up -d
   ```

4. **Verifique o status:**
   ```bash
   docker-compose ps
   ```
