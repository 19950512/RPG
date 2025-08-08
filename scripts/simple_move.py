#!/usr/bin/env python3
"""
Teste direto de movimento - versão simplificada
"""

import asyncio
import grpc
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
import player_pb2
import player_pb2_grpc

async def simple_move_test():
    print("=== TESTE SIMPLES DE MOVIMENTO ===")
    
    # Token JWT válido (extraído dos logs)
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJuYW1laWQiOiIwZGQ5Yjg4My04ZWRiLTQ2MzQtYTA5Ni1hMWJjZjkzY2ZhNDMiLCJuYmYiOjE3NTQ1OTgxNDEsImV4cCI6MTc1NDYwMTc0MSwiaWF0IjoxNzU0NTk4MTQxfQ.M5lUddJfUj6xGQxVYGMHj8nnJvzQlYI7Jp5qr8Q4UKw"
    metadata = (('authorization', f'Bearer {token}'),)
    
    channel = grpc.aio.insecure_channel('localhost:5001')
    player_stub = player_pb2_grpc.PlayerServiceStub(channel)
    
    try:
        print("1. Tentando mover personagem...")
        move_request = player_pb2.PlayerMoveRequest(
            target_x=250.0,
            target_y=250.0,
            movement_type="walk"
        )
        
        response = await player_stub.MovePlayer(move_request, metadata=metadata)
        print(f"Resposta: success={response.success}, message='{response.message}'")
        
    except grpc.RpcError as e:
        print(f"Erro: {e.code()} - {e.details()}")
    except Exception as e:
        print(f"Erro: {e}")
    finally:
        await channel.close()

if __name__ == "__main__":
    asyncio.run(simple_move_test())
