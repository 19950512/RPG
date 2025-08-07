#!/usr/bin/env python3
"""
Cliente simples para testar conexão básica com o GameServer
"""

import asyncio
import grpc
import sys
import os

# Adicionar o diretório de protos ao path
sys.path.insert(0, os.path.dirname(__file__))

import auth_pb2
import auth_pb2_grpc

async def test_simple_connection():
    """Teste simples de conexão e autenticação"""
    
    # Tentar conexão insegura primeiro
    print("Testando conexão insegura...")
    try:
        channel = grpc.aio.insecure_channel('localhost:5001')
        auth_stub = auth_pb2_grpc.AuthServiceStub(channel)
        
        # Tentar criar conta
        print("Criando nova conta...")
        request = auth_pb2.CreateAccountRequest(
            email="simpletest@test.com", 
            password="testpass123"
        )
        
        response = await auth_stub.CreateAccount(request)
        print(f"Resposta: success={response.success}, message='{response.message}'")
        
        if response.success or "already exists" in response.message.lower():
            # Tentar login
            print("Fazendo login...")
            login_request = auth_pb2.LoginRequest(
                email="simpletest@test.com",
                password="testpass123"
            )
            
            login_response = await auth_stub.Login(login_request)
            print(f"Login: success={login_response.success}, message='{login_response.message}'")
            
            if login_response.success:
                print(f"✓ Token recebido: {login_response.jwt_token[:50]}...")
        
        await channel.close()
        print("✓ Teste concluído com sucesso!")
        
    except Exception as e:
        print(f"✗ Erro: {e}")

if __name__ == "__main__":
    print("=== TESTE SIMPLES DE CONEXÃO ===")
    asyncio.run(test_simple_connection())
