# Game Server - Realtime gRPC Backend

Um servidor backend de jogo realtime robusto construído com C# (.NET 8), gRPC, PostgreSQL e Docker, projetado para suportar milhões de conexões simultâneas.

## 🚀 Características Principais

- **Backend C# com ASP.NET Core gRPC** - Comunicação exclusivamente via gRPC
- **Segurança Robusta** - TLS obrigatório + Autenticação JWT
- **Banco PostgreSQL** - Com Entity Framework Core e otimizações de performance
- **Docker & Docker Compose** - Ambiente isolado e escalável
- **Arquitetura Escalável** - Preparado para milhões de conexões simultâneas
- **Load Balancing** - Nginx configurado para alta disponibilidade

## 📋 Requisitos

- Docker & Docker Compose
- .NET 8 SDK (para desenvolvimento local)
- OpenSSL (para geração de certificados)

## 🏗️ Arquitetura

### Banco de Dados
- **Accounts** - Contas de usuário com email único e senha hash
- **Players** - Personagens vinculados às contas
- **AuthTokens** - Tokens JWT válidos com expiração

### Serviços gRPC
- **AuthService** - Criação de conta e login
- **PlayerService** - Gerenciamento de personagens (requer autenticação)

### Segurança
- TLS obrigatório em todas as conexões
- JWT com interceptor gRPC para autenticação
- BCrypt para hash de senhas
- Middleware de autorização

## 🚀 Início Rápido

### Desenvolvimento

1. **Clone o repositório e entre no diretório:**
   ```bash
   cd /home/github/RPG
   ```

2. **Execute o script de configuração de desenvolvimento:**
   ```bash
   ./scripts/setup-dev.sh
   ```

3. **O ambiente estará disponível em:**
   - Game Server gRPC: `https://localhost:5001`
   - PostgreSQL: `localhost:5432`
   - Database: `gameserver`
   - Usuário: `gameuser` / Senha: `gamepass123`

### Produção

1. **Coloque seus certificados CA no diretório `./certs/`:**
   - `gameserver.crt`
   - `gameserver.key`
   - `gameserver.pfx`

2. **Execute o deploy de produção:**
   ```bash
   ./scripts/deploy-prod.sh
   ```

## 🧪 Testando a API

### Usar grpcurl para testar:

1. **Criar uma conta:**
   ```bash
   grpcurl -insecure -d '{"email":"test@example.com","password":"password123"}' \
     localhost:5001 auth.AuthService/CreateAccount
   ```

2. **Fazer login:**
   ```bash
   grpcurl -insecure -d '{"email":"test@example.com","password":"password123"}' \
     localhost:5001 auth.AuthService/Login
   ```

3. **Criar personagem (com JWT token):**
   ```bash
   grpcurl -insecure -H "authorization: Bearer YOUR_JWT_TOKEN" \
     -d '{"name":"MyCharacter","vocation":"Knight"}' \
     localhost:5001 player.PlayerService/CreateCharacter
   ```

4. **Listar personagens:**
   ```bash
   grpcurl -insecure -H "authorization: Bearer YOUR_JWT_TOKEN" \
     -d '{}' localhost:5001 player.PlayerService/ListCharacters
   ```

## 🗂️ Estrutura do Projeto

```
GameServer/
├── src/GameServer/
│   ├── Models/              # Entidades do EF Core
│   ├── Data/               # DbContext e configurações
│   ├── Services/           # Implementações dos serviços gRPC
│   ├── Interceptors/       # Middleware de autenticação
│   ├── Protos/            # Definições Protocol Buffers
│   └── Program.cs         # Configuração e startup
├── scripts/               # Scripts de automação
├── nginx/                 # Configuração do load balancer
├── certs/                # Certificados TLS
├── docker-compose.yml    # Produção
├── docker-compose.dev.yml # Desenvolvimento
└── Dockerfile           # Imagem do servidor
```

## ⚙️ Configuração

### Variáveis de Ambiente

- `ConnectionStrings__DefaultConnection` - String de conexão PostgreSQL
- `Jwt__SecretKey` - Chave secreta para assinatura JWT
- `Jwt__ExpirationMinutes` - Tempo de expiração do token
- `ASPNETCORE_ENVIRONMENT` - Ambiente (Development/Production)

### Configurações de Performance

- **PostgreSQL** otimizado para 1000+ conexões simultâneas
- **Nginx** configurado com rate limiting e load balancing
- **Redis** para cache e sessões (futuro)
- **gRPC** com buffers otimizados para alta throughput

## 🔒 Segurança

- **TLS 1.2/1.3** obrigatório
- **JWT** com assinatura HMAC-SHA256
- **BCrypt** para hash de senhas
- **Rate limiting** no Nginx
- **Headers de segurança** configurados
- **Usuário não-root** nos containers

## 📊 Monitoramento

### Logs
```bash
# Logs do servidor
docker-compose logs -f gameserver

# Logs do PostgreSQL
docker-compose logs -f postgres
```

### Health Checks
- Endpoint: `https://localhost:5001/health`
- Checks automáticos no Docker Compose

### Banco de Dados
```bash
# Conectar ao PostgreSQL
docker-compose exec postgres psql -U gameuser -d gameserver

# Ver conexões ativas
SELECT count(*) FROM pg_stat_activity;
```

## 🔧 Desenvolvimento

### Migrations do Entity Framework

```bash
# Adicionar nova migration
dotnet ef migrations add MigrationName -p src/GameServer

# Aplicar migrations
dotnet ef database update -p src/GameServer
```

### Build Local

```bash
# Restaurar dependências
dotnet restore src/GameServer/GameServer.csproj

# Build
dotnet build src/GameServer/GameServer.csproj

# Run (desenvolvimento)
cd src/GameServer && dotnet run
```

## 🚀 Escalabilidade

O projeto está preparado para scaling horizontal:

1. **Load Balancer** - Nginx configurado para múltiplas instâncias
2. **Stateless Services** - JWT para autenticação sem estado
3. **Connection Pooling** - PostgreSQL otimizado
4. **Container Orchestration** - Pronto para Kubernetes
5. **Caching Layer** - Redis disponível para implementação

### Para adicionar mais instâncias:

```yaml
# Em docker-compose.yml
gameserver2:
  build: .
  environment:
    - ASPNETCORE_URLS=https://+:5001
  # ... mesma configuração

# Atualizar upstream no nginx.conf
upstream gameserver_backend {
    server gameserver:5001;
    server gameserver2:5001;
}
```

## 📚 Próximos Passos

- [ ] Implementar cache Redis para sessões
- [ ] Adicionar métricas com Prometheus
- [ ] Sistema de salas/instâncias de jogo
- [ ] WebSocket para eventos realtime
- [ ] Sistema de chat/mensagens
- [ ] API de administração
- [ ] Backup automático do banco
- [ ] Deploy automatizado com CI/CD

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está licenciado sob a MIT License - veja o arquivo [LICENSE](LICENSE) para detalhes.

---

**Desenvolvido com ❤️ para jogos realtime de alta performance**
