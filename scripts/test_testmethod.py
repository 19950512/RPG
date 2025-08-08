#!/usr/bin/env python3

import grpc
import sys
import os

# Add the parent directory to the path so we can import the generated protobuf files
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.GameServer.Protos import player_pb2
from src.GameServer.Protos import player_pb2_grpc
from src.GameServer.Protos import auth_pb2
from src.GameServer.Protos import auth_pb2_grpc

def test_method():
    # Connect to the server
    channel = grpc.insecure_channel('localhost:5001')
    
    # Create auth stub for login
    auth_stub = auth_pb2_grpc.AuthServiceStub(channel)
    
    print("=== TESTE DO TESTMETHOD ===")
    
    try:
        # Login first
        print("1. Fazendo login...")
        login_response = auth_stub.Login(auth_pb2.LoginRequest(
            username="testuser_testmethod",
            password="password123"
        ))
        
        if not login_response.success:
            print("Login falhou, criando nova conta...")
            register_response = auth_stub.Register(auth_pb2.RegisterRequest(
                username="testuser_testmethod",
                password="password123",
                email="testmethod@test.com"
            ))
            
            if not register_response.success:
                print(f"❌ Falha no registro: {register_response.message}")
                return
                
            # Try login again
            login_response = auth_stub.Login(auth_pb2.LoginRequest(
                username="testuser_testmethod", 
                password="password123"
            ))
            
            if not login_response.success:
                print(f"❌ Falha no login após registro: {login_response.message}")
                return
        
        print("✅ Login realizado!")
        token = login_response.token
        
        # Create player stub
        player_stub = player_pb2_grpc.PlayerServiceStub(channel)
        
        # Create metadata with auth token
        metadata = [('authorization', f'Bearer {token}')]
        
        print("2. Testando TestMethod...")
        try:
            # Call TestMethod
            test_response = player_stub.TestMethod(
                player_pb2.PlayerMoveRequest(
                    target_x=100.0,
                    target_y=200.0,
                    movement_type="walk"
                ),
                metadata=metadata
            )
            
            print(f"✅ TestMethod funcionou! Resposta: {test_response.message}")
            
        except grpc.RpcError as e:
            print(f"❌ Erro RPC no TestMethod: {e.code()} - {e.details()}")
    
    except Exception as e:
        print(f"❌ Erro: {e}")
    
    finally:
        channel.close()

if __name__ == '__main__':
    test_method()
