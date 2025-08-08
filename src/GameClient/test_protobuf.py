#!/usr/bin/env python3

# Teste simples para verificar se conseguimos importar os protobuf gerados
import sys
import os

# Adicionar o diretório pai ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from GameClient.Generated import player_pb2, player_pb2_grpc
    print("✅ Importação dos protobuf realizada com sucesso!")
    
    # Teste para verificar se LeaveWorld está disponível
    if hasattr(player_pb2, 'LeaveWorldRequest'):
        print("✅ LeaveWorldRequest encontrado!")
    else:
        print("❌ LeaveWorldRequest NÃO encontrado!")
        
    if hasattr(player_pb2, 'LeaveWorldResponse'):
        print("✅ LeaveWorldResponse encontrado!")
    else:
        print("❌ LeaveWorldResponse NÃO encontrado!")
        
except Exception as e:
    print(f"❌ Erro ao importar protobuf: {e}")
    import traceback
    traceback.print_exc()
