#!/usr/bin/env python3
import grpc
import player_pb2
import player_pb2_grpc
import auth_pb2
import auth_pb2_grpc
import sys
import os

sys.path.insert(0, '/home/github/RPG/scripts')

def test_method_availability():
    """Teste para verificar se os métodos estão disponíveis"""
    
    # Conectar ao servidor
    channel = grpc.insecure_channel('localhost:5001')
    player_stub = player_pb2_grpc.PlayerServiceStub(channel)
    
    # Verificar se o método MovePlayer existe
    print("Verificando métodos disponíveis no stub:")
    methods = [method for method in dir(player_stub) if not method.startswith('_')]
    for method in methods:
        print(f"  - {method}")
    
    print("\nTestando MovePlayer sem autenticação (esperamos UNAUTHENTICATED, não UNIMPLEMENTED):")
    try:
        request = player_pb2.PlayerMoveRequest(target_x=100.0, target_y=100.0, movement_type="walk")
        response = player_stub.MovePlayer(request)
        print(f"Sucesso inesperado: {response}")
    except grpc.RpcError as e:
        print(f"Erro esperado: {e.code()} - {e.details()}")
        if e.code() == grpc.StatusCode.UNIMPLEMENTED:
            print("⚠️  PROBLEMA: Método não implementado no servidor!")
        elif e.code() == grpc.StatusCode.UNAUTHENTICATED:
            print("✅ CORRETO: Método existe, mas precisa de autenticação")
        else:
            print(f"ℹ️  Outro erro: {e.code()}")
    
    channel.close()

if __name__ == "__main__":
    test_method_availability()
