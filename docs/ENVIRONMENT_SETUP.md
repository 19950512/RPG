# Configuração de Ambiente

Este documento explica como configurar os diferentes ambientes do projeto.

## 📁 Arquivos de Configuração

### Arquivos que devem ser criados localmente:

1. **`dev.env`** - Configuração de desenvolvimento (copiar de `dev.env.example`)
2. **`prod.env`** - Configuração de produção (copiar de `prod.env.example`)
3. **`test_connection.sh`** - Script de teste (copiar de `test_connection.sh.example`)

### Como configurar:

```bash
# Copiar arquivos de exemplo
cp dev.env.example dev.env
cp prod.env.example prod.env
cp test_connection.sh.example test_connection.sh
chmod +x test_connection.sh dev.env prod.env
```

## 🔧 Diferenças entre Ambientes

### Desenvolvimento (`docker-compose.dev.yml`)
- Porta gRPC: 5008
- HTTP nas portas 5001 e 5002
- Container: `gameserver-dev`
- Hot reload habilitado
- Logs detalhados

### Produção (`docker-compose.yml`)
- Porta gRPC: 5008
- HTTPS na porta 5001
- Container: `gameserver`
- Otimizado para performance

## 🚀 Como executar

### Desenvolvimento:
```bash
# 1. Configurar ambiente
source dev.env && source .venv/bin/activate

# 2. Subir containers
docker-compose -f docker-compose.dev.yml up -d

# 3. Executar cliente
cd src && python -m GameClient.main
```

### Produção:
```bash
# 1. Configurar ambiente
source prod.env && source .venv/bin/activate

# 2. Subir containers
docker-compose up -d

# 3. Executar cliente
cd src && python -m GameClient.main
```

## 🧪 Testando

```bash
# Testar conexão e sincronização
./test_connection.sh
```

## 📝 Notas

- Os arquivos `*.env` contêm configurações específicas do ambiente
- Scripts de teste podem variar entre desenvolvedores
- Os arquivos `*.example` servem como template e devem ser versionados
