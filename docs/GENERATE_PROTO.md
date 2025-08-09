# Geração de Arquivos Protobuf

Este documento explica como gerar os arquivos Python a partir dos arquivos `.proto` do projeto.

## Script Automatizado

O projeto inclui um script `generate_proto.py` que automatiza todo o processo de geração dos arquivos protobuf.

### Como usar:

```bash
# Na raiz do projeto
python3 generate_proto.py
```

### O que o script faz:

1. **Instala dependências automaticamente:**
   - `grpcio-tools` - Ferramentas para gerar código Python do gRPC
   - `grpcio` - Biblioteca gRPC para Python
   - `protobuf` - Biblioteca Protocol Buffers

2. **Encontra todos os arquivos `.proto` em:**
   - `src/GameClient/Protos/`

3. **Gera arquivos Python em:**
   - `src/GameClient/Generated/`

### Arquivos gerados:

Para cada arquivo `.proto`, são gerados dois arquivos Python:

- `{nome}_pb2.py` - Classes das mensagens protobuf
- `{nome}_pb2_grpc.py` - Stubs do cliente e servidor gRPC

**Exemplo:**
- `auth.proto` → `auth_pb2.py` + `auth_pb2_grpc.py`
- `player.proto` → `player_pb2.py` + `player_pb2_grpc.py`
- `world.proto` → `world_pb2.py` + `world_pb2_grpc.py`

## Processo Manual (se necessário)

Se você preferir gerar manualmente:

```bash
# Instalar dependências
pip3 install --break-system-packages grpcio-tools grpcio protobuf

# Gerar arquivos (exemplo para auth.proto)
python3 -m grpc_tools.protoc \
  --proto_path=src/GameClient/Protos \
  --python_out=src/GameClient/Generated \
  --grpc_python_out=src/GameClient/Generated \
  src/GameClient/Protos/auth.proto
```

## Quando regenerar

Você precisa regenerar os arquivos sempre que:

1. **Modificar arquivos `.proto`** - Mudanças em mensagens, serviços, campos
2. **Atualizar dependências** - Nova versão do grpcio-tools
3. **Configurar ambiente novo** - Primeiro setup do projeto

## Estrutura dos arquivos

```
src/GameClient/
├── Protos/          # Arquivos .proto originais
│   ├── auth.proto
│   ├── player.proto
│   └── world.proto
└── Generated/       # Arquivos Python gerados
    ├── __init__.py
    ├── auth_pb2.py
    ├── auth_pb2_grpc.py
    ├── player_pb2.py
    ├── player_pb2_grpc.py
    ├── world_pb2.py
    └── world_pb2_grpc.py
```

## Resolução de problemas

### Erro: "externally-managed-environment"

O script usa `--break-system-packages` automaticamente. Se ainda tiver problemas, use um ambiente virtual:

```bash
python3 -m venv venv
source venv/bin/activate
pip install grpcio-tools
python3 generate_proto.py
```

### Erro: "grpc_tools não encontrado"

Execute o script novamente - ele instalará automaticamente as dependências.

### Arquivos não gerados

Verifique se:
1. Os arquivos `.proto` existem em `src/GameClient/Protos/`
2. Não há erros de sintaxe nos arquivos `.proto`
3. As permissões de escrita estão corretas em `src/GameClient/Generated/`
