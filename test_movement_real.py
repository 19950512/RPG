#!/usr/bin/env python3
import grpc
import player_pb2
import player_pb2_grpc
import auth_pb2
import auth_pb2_grpc
import time

def test_complete_movement_flow():
    """Teste completo: login -> personagem -> join world -> movimento real"""
    
    print("=== TESTE COMPLETO DE MOVIMENTO REAL ===")
    
    # Conectar ao servidor
    channel = grpc.insecure_channel('localhost:5001')
    auth_stub = auth_pb2_grpc.AuthServiceStub(channel)
    player_stub = player_pb2_grpc.PlayerServiceStub(channel)
    
    # 1. Login
    print("1. Fazendo login...")
    try:
        login_request = auth_pb2.LoginRequest(
            email="movetest@test.com",
            password="password123"
        )
        login_response = auth_stub.Login(login_request)
        if login_response.success:
            token = login_response.jwt_token
            print("✅ Login realizado!")
        else:
            print(f"❌ Login falhou: {login_response.message}")
            return
    except Exception as e:
        print(f"❌ Erro no login: {e}")
        return
    
    # 2. Listar personagens
    print("2. Listando personagens...")
    try:
        metadata = [('authorization', f'Bearer {token}')]
        list_request = player_pb2.ListCharactersRequest()
        list_response = player_stub.ListCharacters(list_request, metadata=metadata)
        
        if list_response.players:
            character = list_response.players[0]
            print(f"✅ Usando personagem: {character.name}")
            print(f"   Posição inicial: ({character.position_x}, {character.position_y})")
            print(f"   Online: {character.is_online}")
        else:
            print("❌ Nenhum personagem encontrado")
            return
    except grpc.RpcError as e:
        print(f"❌ Erro ao listar personagens: {e.details()}")
        return
    
    # 3. Entrar no mundo (JoinWorld) - sem especificar player_id para usar o primeiro
    print("3. Entrando no mundo...")
    try:
        join_request = player_pb2.JoinWorldRequest()  # Sem player_id
        join_response = player_stub.JoinWorld(join_request, metadata=metadata)
        if join_response.success:
            print(f"✅ Entrou no mundo: {join_response.message}")
            if join_response.player:
                print(f"   Player: {join_response.player.name} at ({join_response.player.position_x}, {join_response.player.position_y})")
                print(f"   Online: {join_response.player.is_online}")
        else:
            print(f"❌ Falha ao entrar no mundo: {join_response.message}")
            return
    except grpc.RpcError as e:
        print(f"❌ Erro ao entrar no mundo: {e.code()} - {e.details()}")
        return
    
    # 4. Série de movimentos
    print("4. Testando movimentos...")
    movements = [
        (100.0, 50.0, "walk"),
        (200.0, 100.0, "run"),
        (150.0, 200.0, "walk"),
        (50.0, 150.0, "run")
    ]
    
    for i, (target_x, target_y, movement_type) in enumerate(movements, 1):
        print(f"   {i}. Movimento para ({target_x}, {target_y}) - {movement_type}")
        try:
            move_request = player_pb2.PlayerMoveRequest(
                target_x=target_x,
                target_y=target_y,
                movement_type=movement_type
            )
            move_response = player_stub.MovePlayer(move_request, metadata=metadata)
            if move_response.success:
                print(f"      ✅ {move_response.message}")
            else:
                print(f"      ❌ Falha: {move_response.message}")
        except grpc.RpcError as e:
            print(f"      ❌ Erro: {e.code()} - {e.details()}")
        
        # Pequeno delay entre movimentos
        time.sleep(0.5)
    
    # 5. Verificar posição final
    print("5. Verificando posição final...")
    try:
        list_response = player_stub.ListCharacters(list_request, metadata=metadata)
        if list_response.players:
            final_character = list_response.players[0]
            print(f"   Posição final: ({final_character.position_x}, {final_character.position_y})")
            print(f"   Estado: {final_character.movement_state}")
            print(f"   Direção: {final_character.facing_direction}")
            print(f"   Online: {final_character.is_online}")
            
            # Verificar se a posição mudou
            if (final_character.position_x != character.position_x or 
                final_character.position_y != character.position_y):
                print("🎉 Personagem se moveu com sucesso!")
                print(f"🎉 Movimento total: ({character.position_x}, {character.position_y}) → ({final_character.position_x}, {final_character.position_y})")
            else:
                print("⚠️  Personagem não se moveu (posição não mudou)")
    except grpc.RpcError as e:
        print(f"❌ Erro ao verificar posição: {e.details()}")
    
    print("\n🎮 Teste de movimento concluído!")

if __name__ == "__main__":
    test_complete_movement_flow()
