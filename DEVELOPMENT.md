# Guia de Desenvolvimento

## 🏗️ Estrutura do Projeto

```
RPG/
├── src/
│   ├── GameServer/          # Servidor C# (.NET 8)
│   │   ├── Services/        # Serviços gRPC
│   │   ├── Models/          # Modelos de dados
│   │   ├── Data/           # Contexto do banco
│   │   └── Protos/         # Definições Protocol Buffer
│   └── GameClient/         # Cliente Python
│       ├── auth/           # Telas de autenticação
│       ├── game/           # Lógica do jogo
│       ├── Generated/      # Arquivos gRPC gerados
│       └── main.py         # Ponto de entrada
├── scripts/                # Scripts de desenvolvimento
├── certs/                  # Certificados SSL
└── docker-compose.yml     # Configuração Docker
```

## 🔄 Fluxo de Desenvolvimento

### 1. Modificando o Servidor (.NET)

```bash
# Após fazer mudanças no código C#:
docker-compose build --no-cache gameserver
docker-compose restart gameserver

# Ver logs para debug:
docker-compose logs -f gameserver
```

### 2. Modificando Protocol Buffers

```bash
# Após alterar arquivos .proto:
cd src/GameServer
dotnet build  # Regenera arquivos C#

cd ../GameClient
python -m grpc_tools.protoc \
    --proto_path=../GameServer/Protos \
    --python_out=Generated \
    --grpc_python_out=Generated \
    ../GameServer/Protos/*.proto
```

### 3. Modificando o Cliente Python

```bash
# Ativar ambiente virtual
source ./activate-env.sh

# Executar cliente
cd src/GameClient
python main.py

# Ou usar o script:
./run-client.sh
```

## 🧪 Testes e Debug

### Testando Conectividade gRPC

```bash
# Listar serviços disponíveis
docker-compose exec gameserver grpcurl -plaintext localhost:50051 list

# Testar um endpoint específico
docker-compose exec gameserver grpcurl -plaintext \
    -d '{"email":"test@test.com","password":"password123"}' \
    localhost:50051 AuthService/Register
```

### Debug do Banco de Dados

```bash
# Acessar PostgreSQL
docker-compose exec postgres psql -U gameuser -d gameserver

# Comandos SQL úteis:
\dt                              # Listar tabelas
SELECT * FROM "Accounts";        # Ver contas
SELECT * FROM "Players";         # Ver jogadores
SELECT * FROM "WorldEntities";   # Ver entidades do mundo
```

### Logs Detalhados

```bash
# Servidor
docker-compose logs -f gameserver

# Banco de dados
docker-compose logs -f postgres

# Todos os serviços
docker-compose logs -f
```

## 🎯 Adicionando Novas Funcionalidades

### 1. Novo Serviço gRPC

1. **Definir no Protocol Buffer** (`src/GameServer/Protos/`)
2. **Implementar o serviço** (`src/GameServer/Services/`)
3. **Registrar no Program.cs**
4. **Regenerar código cliente**
5. **Implementar no cliente Python**

### 2. Novo Modelo de Dados

1. **Criar model** (`src/GameServer/Models/`)
2. **Adicionar ao DbContext** (`src/GameServer/Data/GameDbContext.cs`)
3. **Gerar migração**:
   ```bash
   cd src/GameServer
   dotnet ef migrations add NovoModelo
   ```
4. **Aplicar migração** (automático no Docker)

### 3. Nova Tela no Cliente

1. **Criar classe** em `src/GameClient/game/` ou `src/GameClient/auth/`
2. **Implementar interface Pygame**
3. **Integrar com `main.py`**

## 🔧 Configurações de Ambiente

### Variáveis de Ambiente

Edite `dev.env` para configurações locais:

```env
# Banco de dados
POSTGRES_PASSWORD=gameserver123
POSTGRES_USER=gameuser
POSTGRES_DB=gameserver

# JWT
JWT_SECRET_KEY=sua-chave-secreta-muito-segura

# Servidor
ASPNETCORE_URLS=https://+:50051;http://+:50052
```

### Certificados SSL

```bash
# Regenerar certificados
./scripts/generate-certs.sh

# Verificar certificado
openssl x509 -in certs/gameserver.crt -text -noout
```

## 🚀 Deploy e Performance

### Build de Produção

```bash
# Build otimizado
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

# Deploy em produção
docker-compose -f docker-compose.prod.yml up -d
```

### Monitoramento

```bash
# Performance dos containers
docker stats

# Uso de recursos
docker-compose top

# Conectividade
./test-environment.sh
```

## 📚 Recursos Úteis

- **gRPC Documentation**: https://grpc.io/docs/
- **.NET 8 gRPC**: https://docs.microsoft.com/en-us/aspnet/core/grpc/
- **Entity Framework Core**: https://docs.microsoft.com/en-us/ef/core/
- **Pygame**: https://www.pygame.org/docs/
- **Protocol Buffers**: https://developers.google.com/protocol-buffers

## 🐛 Solução de Problemas

### Erro: "Port already in use"
```bash
docker-compose down
sudo netstat -tulpn | grep 50051
# Matar processo se necessário
```

### Erro: "Connection refused"
```bash
# Verificar se serviços estão rodando
docker-compose ps

# Verificar logs
docker-compose logs gameserver
```

### Erro: "Module not found" (Python)
```bash
# Ativar ambiente virtual
source ./activate-env.sh

# Reinstalar dependências
pip install -r src/GameClient/requirements.txt
```

### Erro de migração do banco
```bash
# Reset completo do banco
docker-compose down -v
docker-compose up -d postgres
# Aguardar e subir gameserver
docker-compose up -d gameserver
```
