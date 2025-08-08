#!/usr/bin/env python3
"""
Teste específico para movimento de personagens
"""

import asyncio
import grpc
import sys
import os
import time

# Adicionar o diretório de protos ao path
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, '/home/github/RPG/src/GameClient/Generated')

import auth_pb2
import auth_pb2_grpc
import player_pb2
import player_pb2_grpc

async def test_movement():
    """Testa especificamente o sistema de movimento"""
    
    print("=== TESTE DE MOVIMENTO ===")
    
    # Conectar ao servidor
    channel = grpc.aio.insecure_channel('localhost:5001')
    auth_stub = auth_pb2_grpc.AuthServiceStub(channel)
    player_stub = player_pb2_grpc.PlayerServiceStub(channel)
    
    try:
        # Login com conta de teste
        print("1. Fazendo login...")
        login_request = auth_pb2.LoginRequest(
            email="test@gameserver.com",
            password="password123"
        )
        
        try:
            login_response = await auth_stub.Login(login_request)
            if not login_response.success:
                print("Login falhou, criando nova conta...")
                unique_email = f"movetest{int(time.time())}@test.com"
                
                # Criar conta
                create_request = auth_pb2.CreateAccountRequest(
                    email=unique_email,
                    password="testpass123"
                )
                await auth_stub.CreateAccount(create_request)
                
                # Tentar login novamente
                login_request.email = unique_email
                login_request.password = "testpass123"
                login_response = await auth_stub.Login(login_request)
        except:
            print("Erro no login, criando nova conta...")
            unique_email = f"movetest{int(time.time())}@test.com"
            
            # Criar conta
            create_request = auth_pb2.CreateAccountRequest(
                email=unique_email,
                password="testpass123"
            )
            await auth_stub.CreateAccount(create_request)
            
            # Login
            login_request = auth_pb2.LoginRequest(
                email=unique_email,
                password="testpass123"
            )
            login_response = await auth_stub.Login(login_request)
        
        if not login_response.success:
            print("❌ Não foi possível fazer login")
            return
            
        print("✅ Login realizado!")
        token = login_response.jwt_token
        metadata = (('authorization', f'Bearer {token}'),)
        
        # Listar personagens
        print("2. Listando personagens...")
        list_request = player_pb2.ListCharactersRequest()
        list_response = await player_stub.ListCharacters(list_request, metadata=metadata)
        
        if not list_response.players:
            print("Nenhum personagem encontrado, criando um...")
            char_name = f"MoveTest{int(time.time())}"
            create_char_request = player_pb2.CreateCharacterRequest(
                name=char_name,
                vocation="Knight"
            )
            char_response = await player_stub.CreateCharacter(create_char_request, metadata=metadata)
            
            if not char_response.success:
                print("❌ Falha ao criar personagem")
                return
                
            print(f"✅ Personagem {char_name} criado!")
            # Recarregar lista
            list_response = await player_stub.ListCharacters(list_request, metadata=metadata)
        
        # Selecionar primeiro personagem
        player = list_response.players[0]
        print(f"3. Usando personagem: {player.name}")
        print(f"   Posição atual: ({player.position_x:.1f}, {player.position_y:.1f})")
        
        # Testar movimento
        print("4. Testando movimento...")
        
        # Movimento 1: Para a direita
        print("   → Movendo para (200, 150)...")
        move_request = player_pb2.PlayerMoveRequest(
            target_x=200.0,
            target_y=150.0,
            movement_type="walk"
        )
        
        try:
            move_response = await player_stub.MovePlayer(move_request, metadata=metadata)
            if move_response.success:
                print("   ✅ Movimento realizado com sucesso!")
            else:
                print(f"   ❌ Falha no movimento: {move_response.message}")
        except grpc.RpcError as e:
            print(f"   ❌ Erro RPC no movimento: {e.code()} - {e.details()}")
        
        # Aguardar um pouco
        await asyncio.sleep(1)
        
        # Movimento 2: Para baixo
        print("   ↓ Movendo para (200, 300)...")
        move_request2 = player_pb2.PlayerMoveRequest(
            target_x=200.0,
            target_y=300.0,
            movement_type="run"
        )
        
        try:
            move_response2 = await player_stub.MovePlayer(move_request2, metadata=metadata)
            if move_response2.success:
                print("   ✅ Movimento realizado com sucesso!")
            else:
                print(f"   ❌ Falha no movimento: {move_response2.message}")
        except grpc.RpcError as e:
            print(f"   ❌ Erro RPC no movimento: {e.code()} - {e.details()}")
        
        # Verificar posição final
        print("5. Verificando posição final...")
        final_list = await player_stub.ListCharacters(list_request, metadata=metadata)
        final_player = final_list.players[0]
        print(f"   Posição final: ({final_player.position_x:.1f}, {final_player.position_y:.1f})")
        
        if (final_player.position_x != player.position_x or 
            final_player.position_y != player.position_y):
            print("🎉 MOVIMENTO FUNCIONANDO! Personagem mudou de posição!")
        else:
            print("⚠️  Personagem não se moveu (posição não mudou)")
            
    except Exception as e:
        print(f"❌ Erro durante teste: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await channel.close()

if __name__ == "__main__":
    asyncio.run(test_movement())
