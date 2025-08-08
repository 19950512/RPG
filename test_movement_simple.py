#!/usr/bin/env python3
import grpc
import player_pb2
import player_pb2_grpc
import auth_pb2
import auth_pb2_grpc

def test_movement_simple():
    """Teste simples de movimento"""
    print("=== TESTE MOVIMENTO SIMPLES ===")
    
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
    
    # 2. Metadata para autenticação
    metadata = [('authorization', f'Bearer {token}')]
    
    # 3. JoinWorld
    print("2. JoinWorld...")
    try:
        join_request = player_pb2.JoinWorldRequest()
        join_response = player_stub.JoinWorld(join_request, metadata=metadata)
        print(f"✅ JoinWorld: {join_response.message}")
    except grpc.RpcError as e:
        print(f"❌ Erro JoinWorld: {e.code()} - {e.details()}")
        return
    
    # 4. Movimento
    print("3. Movimento...")
    try:
        move_request = player_pb2.PlayerMoveRequest(
            target_x=100.0,
            target_y=200.0,
            movement_type="walk"
        )
        move_response = player_stub.MovePlayer(move_request, metadata=metadata)
        if move_response.success:
            print(f"✅ Movimento: {move_response.message}")
        else:
            print(f"❌ Movimento falhou: {move_response.message}")
    except grpc.RpcError as e:
        print(f"❌ Erro movimento: {e.code()} - {e.details()}")
    
    # 5. Verificar posição
    print("4. Verificar posição...")
    try:
        list_request = player_pb2.ListCharactersRequest()
        list_response = player_stub.ListCharacters(list_request, metadata=metadata)
        if list_response.players:
            player = list_response.players[0]
            print(f"✅ Posição: ({player.position_x}, {player.position_y})")
            print(f"   Estado: {player.movement_state}")
            print(f"   Direção: {player.facing_direction}")
            print(f"   Online: {player.is_online}")
    except grpc.RpcError as e:
        print(f"❌ Erro verificar: {e.details()}")
    
    print("Teste concluído!")

if __name__ == "__main__":
    test_movement_simple()
