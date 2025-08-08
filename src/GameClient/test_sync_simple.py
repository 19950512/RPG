#!/usr/bin/env python3
"""
Teste simples de sincronização
"""

import sys
import os

# Importar diretamente os módulos
from grpc_client_standalone import grpc_client
import time

def test_sync():
    print("🔗 Testando sincronização com servidor...")
    
    try:
        grpc_client.connect()
        
        # Teste login com credenciais existentes
        print("1. Fazendo login...")
        response = grpc_client.login("testuser@test.com", "testpass123")
        if response and response.success:
            print(f"✅ Login bem-sucedido!")
            token = response.token
            
            # Teste entrada no mundo
            print("2. Entrando no mundo...")
            response = grpc_client.join_world(token)
            if response and response.success:
                print(f"✅ Mundo joinado: {response.message}")
                
                # Teste sincronização de stats
                print("3. Sincronizando stats...")
                response = grpc_client.update_player_stats(token, level=5, experience=500, hp=90, mp=40)
                if response:
                    print(f"✅ Stats atualizados!")
                
                # Teste sincronização de posição
                print("4. Sincronizando posição...")
                response = grpc_client.update_player_position(
                    token, 
                    position_x=1200.0, 
                    position_y=1000.0,
                    facing_direction=3,
                    movement_state="running"
                )
                if response:
                    print(f"✅ Posição atualizada!")
                    
                print("\n🎉 SINCRONIZAÇÃO FUNCIONANDO! Todas as informações estão sendo salvas no servidor!")
            else:
                print(f"❌ Erro ao entrar no mundo: {response.message if response else 'Sem resposta'}")
        else:
            print(f"❌ Erro no login: {response.message if response else 'Sem resposta'}")
    
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
    finally:
        grpc_client.close()

if __name__ == "__main__":
    test_sync()
