#!/usr/bin/env python3
"""
Teste de sincronização com o servidor sem interface gráfica
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src', 'GameClient'))

# Adicionar o diretório GameClient ao path
client_path = os.path.join(os.path.dirname(__file__), 'src', 'GameClient')
sys.path.insert(0, client_path)

from grpc_client import grpc_client
import time

def test_server_connection():
    """Testa conexão básica com o servidor"""
    print("🔗 Testando conexão com o servidor...")
    
    try:
        # Teste de login
        print("1. Testando registro de conta...")
        grpc_client.connect()
        
        # Registrar nova conta
        response = grpc_client.register("testuser@test.com", "testpass123")
        if response and response.success:
            print(f"✅ Registro bem-sucedido: {response.message}")
        else:
            print(f"❌ Falha no registro: {response.message if response else 'Sem resposta'}")
            
        # Login
        print("2. Testando login...")
        response = grpc_client.login("testuser@test.com", "testpass123")
        if response and response.success:
            print(f"✅ Login bem-sucedido! Token: {response.token[:20]}...")
            token = response.token
        else:
            print(f"❌ Falha no login: {response.message if response else 'Sem resposta'}")
            return
        
        # Criar personagem
        print("3. Testando criação de personagem...")
        response = grpc_client.create_character(token, "TestPlayer", "Warrior")
        if response and response.success:
            print(f"✅ Personagem criado: {response.message}")
        else:
            print(f"❌ Falha na criação: {response.message if response else 'Sem resposta'}")
            
        # Listar personagens
        print("4. Testando listagem de personagens...")
        response = grpc_client.list_characters(token)
        if response and response.success:
            print(f"✅ Personagens encontrados: {len(response.characters)}")
            if response.characters:
                char = response.characters[0]
                print(f"   - Nome: {char.name}, Level: {char.level}, EXP: {char.experience}")
        else:
            print(f"❌ Falha na listagem: {response.message if response else 'Sem resposta'}")
            
        # Entrar no mundo
        print("5. Testando entrada no mundo...")
        response = grpc_client.join_world(token)
        if response and response.success:
            print(f"✅ Entrou no mundo: {response.message}")
            if response.player:
                print(f"   - Posição: ({response.player.position_x}, {response.player.position_y})")
                print(f"   - Stats: Level {response.player.level}, EXP {response.player.experience}")
                print(f"   - HP: {response.player.current_hp}/{response.player.max_hp}")
        else:
            print(f"❌ Falha ao entrar no mundo: {response.message if response else 'Sem resposta'}")
            
        # Teste sincronização de stats
        print("6. Testando sincronização de stats...")
        response = grpc_client.update_player_stats(token, level=2, experience=150, hp=95, mp=45)
        if response and response.success:
            print(f"✅ Stats sincronizados com sucesso!")
        else:
            print(f"❌ Falha na sincronização de stats: {response.message if response else 'Sem resposta'}")
            
        # Teste sincronização de posição
        print("7. Testando sincronização de posição...")
        response = grpc_client.update_player_position(
            token,
            position_x=1000.0, 
            position_y=800.0,
            facing_direction=2,
            movement_state="walking"
        )
        if response and response.success:
            print(f"✅ Posição sincronizada com sucesso!")
        else:
            print(f"❌ Falha na sincronização de posição: {response.message if response else 'Sem resposta'}")
            
        # Teste movimento
        print("8. Testando comando de movimento...")
        response = grpc_client.move_player(token, 1100.0, 900.0, "run")
        if response and response.success:
            print(f"✅ Movimento enviado: {response.message}")
        else:
            print(f"❌ Falha no movimento: {response.message if response else 'Sem resposta'}")
            
        print("\n🎉 Todos os testes de sincronização concluídos!")
        
    except Exception as e:
        print(f"❌ Erro durante os testes: {e}")
        import traceback
        traceback.print_exc()
    finally:
        grpc_client.close()

if __name__ == "__main__":
    test_server_connection()
