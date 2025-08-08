#!/usr/bin/env python3
import grpc
import player_pb2
import player_pb2_grpc
import auth_pb2
import auth_pb2_grpc

def test_join_world():
    """Teste simples do JoinWorld"""
    print("=== TESTE JOINWORLD ===")
    
    # Conectar ao servidor
    channel = grpc.insecure_channel('localhost:5001')
    auth_stub = auth_pb2_grpc.AuthServiceStub(channel)
    player_stub = player_pb2_grpc.PlayerServiceStub(channel)
    
    # 1. Login
    print("1. Login...")
    try:
        login_request = auth_pb2.LoginRequest(
            email="movetest@test.com",
            password="password123"
        )
        login_response = auth_stub.Login(login_request)
        if login_response.success:
            token = login_response.jwt_token
            print("✅ Login OK")
        else:
            print(f"❌ Login falhou: {login_response.message}")
            return
    except Exception as e:
        print(f"❌ Erro no login: {e}")
        return
    
    # 2. Testar JoinWorld
    print("2. Testando JoinWorld...")
    try:
        metadata = [('authorization', f'Bearer {token}')]
        join_request = player_pb2.JoinWorldRequest()
        join_response = player_stub.JoinWorld(join_request, metadata=metadata)
        print(f"✅ JoinWorld: {join_response.message}")
    except grpc.RpcError as e:
        print(f"❌ Erro JoinWorld: {e.code()} - {e.details()}")
    
    print("Teste concluído!")

if __name__ == "__main__":
    test_join_world()
