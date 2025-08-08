#!/usr/bin/env python3
import grpc
import player_pb2
import player_pb2_grpc
import auth_pb2
import auth_pb2_grpc
import time

def test_multiple_movements():
    """Teste com múltiplos movimentos"""
    print("=== TESTE MÚLTIPLOS MOVIMENTOS ===")
    
    # Conectar ao servidor
    channel = grpc.insecure_channel('localhost:5001')
    auth_stub = auth_pb2_grpc.AuthServiceStub(channel)
    player_stub = player_pb2_grpc.PlayerServiceStub(channel)
    
    # Login
    login_request = auth_pb2.LoginRequest(
        email="movetest@test.com",
        password="password123"
    )
    login_response = auth_stub.Login(login_request)
    token = login_response.jwt_token
    metadata = [('authorization', f'Bearer {token}')]
    
    # JoinWorld
    join_request = player_pb2.JoinWorldRequest()
    join_response = player_stub.JoinWorld(join_request, metadata=metadata)
    print(f"🌍 {join_response.message}")
    
    # Sequência de movimentos
    movements = [
        (50, 50, "walk"),
        (150, 100, "run"),
        (300, 200, "walk"),
        (250, 350, "run"),
        (100, 300, "walk")
    ]
    
    print(f"\n🎮 Iniciando sequência de {len(movements)} movimentos:")
    
    for i, (x, y, move_type) in enumerate(movements, 1):
        print(f"\n  {i}. Movendo para ({x}, {y}) - {move_type}")
        
        move_request = player_pb2.PlayerMoveRequest(
            target_x=float(x),
            target_y=float(y),
            movement_type=move_type
        )
        
        try:
            move_response = player_stub.MovePlayer(move_request, metadata=metadata)
            if move_response.success:
                print(f"     ✅ {move_response.message}")
            else:
                print(f"     ❌ {move_response.message}")
        except grpc.RpcError as e:
            print(f"     ❌ Erro: {e.details()}")
        
        # Verificar posição atual
        list_request = player_pb2.ListCharactersRequest()
        list_response = player_stub.ListCharacters(list_request, metadata=metadata)
        if list_response.players:
            player = list_response.players[0]
            directions = ["North", "East", "South", "West"]
            direction_name = directions[player.facing_direction] if 0 <= player.facing_direction < 4 else "Unknown"
            print(f"     📍 Real: ({player.position_x}, {player.position_y}) facing {direction_name} ({player.movement_state})")
        
        time.sleep(1)  # Pequena pausa entre movimentos
    
    print(f"\n🎉 Teste de múltiplos movimentos concluído!")

if __name__ == "__main__":
    test_multiple_movements()
