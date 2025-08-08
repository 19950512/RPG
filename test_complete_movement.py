#!/usr/bin/env python3
import grpc
import player_pb2
import player_pb2_grpc
import auth_pb2
import auth_pb2_grpc
import time

def test_complete_movement():
    """Teste completo: login -> personagem -> join world -> movimento"""
    
    print("=== TESTE COMPLETO DE MOVIMENTO ===")
    
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
        if not login_response.success:
            # Criar conta se não existe
            print("Login falhou, criando nova conta...")
            create_request = auth_pb2.CreateAccountRequest(
                email="movetest@test.com",
                password="password123"
            )
            create_response = auth_stub.CreateAccount(create_request)
            if create_response.success:
                # Tentar login novamente
                login_response = auth_stub.Login(login_request)
        
        if login_response.success:
            token = login_response.jwt_token
            print("✅ Login realizado!")
        else:
            print(f"❌ Falha no login: {login_response.message}")
            return
    except grpc.RpcError as e:
        print(f"❌ Erro no login: {e.details()}")
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
        else:
            print("Nenhum personagem encontrado, criando um...")
            create_request = player_pb2.CreateCharacterRequest(
                name=f"TestPlayer{int(time.time())}",
                vocation="Knight"
            )
            create_response = player_stub.CreateCharacter(create_request, metadata=metadata)
            if create_response.success:
                print(f"✅ Personagem {create_response.character.name} criado!")
                character = create_response.character
            else:
                print(f"❌ Falha ao criar personagem: {create_response.message}")
                return
    except grpc.RpcError as e:
        print(f"❌ Erro ao listar personagens: {e.details()}")
        return
    
    print(f"   Posição inicial: ({character.position_x}, {character.position_y})")
    print(f"   Online: {character.is_online}")
    
    # 3. Entrar no mundo (JoinWorld)
    print("3. Entrando no mundo...")
    try:
        join_request = player_pb2.JoinWorldRequest()
        join_response = player_stub.JoinWorld(join_request, metadata=metadata)
        if join_response.success:
            print(f"✅ Entrou no mundo: {join_response.message}")
        else:
            print(f"❌ Falha ao entrar no mundo: {join_response.message}")
    except grpc.RpcError as e:
        print(f"❌ Erro ao entrar no mundo: {e.code()} - {e.details()}")
        return
    
    # 4. Testar movimento
    print("4. Testando movimento...")
    try:
        move_request = player_pb2.PlayerMoveRequest(
            target_x=200.0,
            target_y=150.0,
            movement_type="walk"
        )
        move_response = player_stub.MovePlayer(move_request, metadata=metadata)
        if move_response.success:
            print(f"✅ Movimento realizado: {move_response.message}")
        else:
            print(f"❌ Falha no movimento: {move_response.message}")
    except grpc.RpcError as e:
        print(f"❌ Erro no movimento: {e.code()} - {e.details()}")
    
    # 5. Verificar posição final
    print("5. Verificando posição final...")
    try:
        list_response = player_stub.ListCharacters(list_request, metadata=metadata)
        if list_response.players:
            final_character = list_response.players[0]
            print(f"   Posição final: ({final_character.position_x}, {final_character.position_y})")
            print(f"   Online: {final_character.is_online}")
            
            # Verificar se a posição mudou
            if (final_character.position_x != character.position_x or 
                final_character.position_y != character.position_y):
                print("🎉 Personagem se moveu com sucesso!")
            else:
                print("⚠️  Personagem não se moveu (posição não mudou)")
    except grpc.RpcError as e:
        print(f"❌ Erro ao verificar posição: {e.details()}")

if __name__ == "__main__":
    test_complete_movement()
