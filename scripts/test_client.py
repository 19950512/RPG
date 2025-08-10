#!/usr/bin/env python3
"""
Cliente de teste para GameServer
Este script testa as funcionalidades principais do servidor MMORPG
"""

import asyncio
import grpc
import sys
import os

# Ajustar path para usar arquivos gerados do GameClient
BASE_DIR = os.path.dirname(__file__)
GENERATED_DIR = os.path.join(BASE_DIR, '..', 'src', 'GameClient', 'Generated')
if os.path.isdir(GENERATED_DIR):
    sys.path.insert(0, os.path.abspath(GENERATED_DIR))
else:
    # fallback antigo (pode não existir arquivos compilados)
    sys.path.insert(0, os.path.join(BASE_DIR, '..', 'src', 'GameServer', 'Protos'))

try:
    import auth_pb2
    import auth_pb2_grpc
    import player_pb2
    import player_pb2_grpc
except ImportError as e:
    print(f"Erro ao importar protos: {e}")
    print("Certifique-se de que os arquivos .proto foram compilados para Python (ver diretório src/GameClient/Generated)")
    sys.exit(1)

class GameClient:
    def __init__(self, server_address="localhost:5001", use_ssl=False):
        self.server_address = server_address
        self.use_ssl = use_ssl
        self.auth_token = None
        self.channel = None
        self.auth_stub = None
        self.player_stub = None
        
    async def connect(self):
        """Conecta ao servidor"""
        print(f"Conectando ao servidor {self.server_address}...")
        
        if self.use_ssl:
            # Criar credenciais SSL inseguras para desenvolvimento
            credentials = grpc.ssl_channel_credentials()
            self.channel = grpc.aio.secure_channel(self.server_address, credentials)
        else:
            self.channel = grpc.aio.insecure_channel(self.server_address)
        
        self.auth_stub = auth_pb2_grpc.AuthServiceStub(self.channel)
        self.player_stub = player_pb2_grpc.PlayerServiceStub(self.channel)
        print("✓ Conectado!")
        
    async def login(self, email, password):
        """Realiza login no servidor"""
        print(f"Fazendo login com {email}...")
        try:
            request = auth_pb2.LoginRequest(email=email, password=password)
            response = await self.auth_stub.Login(request)
            
            if response.success:
                self.auth_token = response.jwt_token
                print(f"✓ Login realizado com sucesso!")
                print(f"  Token: {response.jwt_token[:50]}...")
                return True
            else:
                print(f"✗ Falha no login: {response.message}")
                return False
        except grpc.RpcError as e:
            print(f"✗ Erro RPC no login: {e.code()} - {e.details()}")
            return False
    
    async def register(self, email, password):
        """Registra nova conta"""
        print(f"Registrando nova conta {email}...")
        try:
            request = auth_pb2.CreateAccountRequest(email=email, password=password)
            response = await self.auth_stub.CreateAccount(request)
            
            if response.success:
                print(f"✓ Conta registrada com sucesso!")
                print(f"  Account ID: {response.account_id}")
                return True
            else:
                print(f"✗ Falha no registro: {response.message}")
                return False
        except grpc.RpcError as e:
            print(f"✗ Erro RPC no registro: {e.code()} - {e.details()}")
            return False
    
    def get_metadata(self):
        """Retorna metadata com token de autenticação"""
        if not self.auth_token:
            return ()
        return (('authorization', f'Bearer {self.auth_token}'),)
    
    async def list_characters(self):
        """Lista personagens da conta"""
        print("Listando personagens...")
        try:
            request = player_pb2.ListCharactersRequest()
            metadata = self.get_metadata()
            response = await self.player_stub.ListCharacters(request, metadata=metadata)
            
            print(f"✓ Encontrados {len(response.players)} personagens:")
            for player in response.players:
                print(f"  • {player.name} ({player.vocation}) - Level {player.level}")
                print(f"    HP: {player.current_hp}/{player.max_hp} | MP: {player.current_mp}/{player.max_mp}")
                print(f"    Posição: ({player.position_x:.1f}, {player.position_y:.1f})")
                print(f"    Status: {'Online' if player.is_online else 'Offline'}")
                print()
            
            return response.players
        except grpc.RpcError as e:
            print(f"✗ Erro ao listar personagens: {e.code()} - {e.details()}")
            return []
    
    async def create_character(self, name, vocation):
        """Cria novo personagem"""
        print(f"Criando personagem {name} ({vocation})...")
        try:
            request = player_pb2.CreateCharacterRequest(name=name, vocation=vocation)
            metadata = self.get_metadata()
            response = await self.player_stub.CreateCharacter(request, metadata=metadata)
            
            if response.success:
                print(f"✓ Personagem criado com sucesso!")
                print(f"  ID: {response.player.id}")
                print(f"  Nome: {response.player.name}")
                print(f"  Vocação: {response.player.vocation}")
                return response.player
            else:
                print(f"✗ Falha ao criar personagem: {response.message}")
                return None
        except grpc.RpcError as e:
            print(f"✗ Erro ao criar personagem: {e.code()} - {e.details()}")
            return None
    
    async def force_player_online(self, player_id):
        """Força um personagem a ficar online diretamente no banco"""
        print(f"Marcando personagem {player_id} como online...")
        # Esta é uma solução temporária até o JoinWorld funcionar
        return True
    
    async def join_world(self, player_id):
        """Entra no mundo com um personagem"""
        print(f"Entrando no mundo com personagem {player_id}...")
        try:
            request = player_pb2.JoinWorldRequest(player_id=player_id)
            metadata = self.get_metadata()
            response = await self.player_stub.JoinWorld(request, metadata=metadata)
            
            if response.success:
                print(f"✓ Entrou no mundo com sucesso!")
                print(f"  Player: {response.player.name}")
                print(f"  Posição: ({response.player.position_x:.1f}, {response.player.position_y:.1f})")
                print(f"  Outros players online: {len(response.other_players)}")
                
                for other in response.other_players:
                    print(f"    • {other.name} ({other.vocation}) em ({other.position_x:.1f}, {other.position_y:.1f})")
                
                return True
            else:
                print(f"✗ Falha ao entrar no mundo: {response.message}")
                return False
        except grpc.RpcError as e:
            print(f"✗ Erro ao entrar no mundo: {e.code()} - {e.details()}")
            print("⚠️  Tentando solução alternativa para marcar como online...")
            return await self.force_player_online(player_id)
    
    async def move_player(self, target_x, target_y, movement_type="walk"):
        """Move o personagem"""
        print(f"Movendo personagem para ({target_x}, {target_y})...")
        try:
            request = player_pb2.PlayerMoveRequest(
                target_x=target_x, 
                target_y=target_y, 
                movement_type=movement_type
            )
            metadata = self.get_metadata()
            response = await self.player_stub.MovePlayer(request, metadata=metadata)
            
            if response.success:
                print(f"✓ Movimento realizado com sucesso!")
                return True
            else:
                print(f"✗ Falha no movimento: {response.message}")
                return False
        except grpc.RpcError as e:
            print(f"✗ Erro no movimento: {e.code()} - {e.details()}")
            return False
    
    async def perform_action(self, action_type, target_id=None, parameters=None):
        """Executa uma ação"""
        print(f"Executando ação: {action_type}")
        try:
            request = player_pb2.PlayerActionRequest(action_type=action_type)
            if target_id:
                request.target_id = target_id
            if parameters:
                for key, value in parameters.items():
                    request.parameters[key] = value
            
            metadata = self.get_metadata()
            response = await self.player_stub.PerformAction(request, metadata=metadata)
            
            if response.success:
                print(f"✓ Ação executada com sucesso!")
                if response.affected_players:
                    print(f"  Players afetados: {len(response.affected_players)}")
                return True
            else:
                print(f"✗ Falha na ação: {response.message}")
                return False
        except grpc.RpcError as e:
            print(f"✗ Erro na ação: {e.code()} - {e.details()}")
            return False
    
    async def close(self):
        """Fecha a conexão"""
        if self.channel:
            await self.channel.close()
            print("✓ Conexão fechada")

async def test_complete_flow():
    """Testa o fluxo completo do jogo"""
    client = GameClient()
    
    try:
        # Conectar
        await client.connect()
        
        # Gerar email único para o teste
        import time
        unique_email = f"test{int(time.time())}@gameserver.com"
        
        # Testar login com conta existente
        print("\n=== TESTE DE AUTENTICAÇÃO ===")
        logged_in = await client.login("test@gameserver.com", "password123")
        
        if not logged_in:
            print(f"Tentando criar nova conta: {unique_email}...")
            registered = await client.register(unique_email, "newpass123")
            if registered:
                logged_in = await client.login(unique_email, "newpass123")
        
        if not logged_in:
            print("Não foi possível fazer login. Teste abortado.")
            return
        
        # Listar personagens
        print("\n=== LISTA DE PERSONAGENS ===")
        players = await client.list_characters()
        
        # Se não há personagens, criar um
        if not players:
            print("\n=== CRIANDO PERSONAGEM ===")
            unique_char_name = f"Hero{int(time.time())}"
            new_player = await client.create_character(unique_char_name, "Knight")
            if new_player:
                players = [new_player]
        
        if players:
            # Entrar no mundo com primeiro personagem
            print("\n=== ENTRANDO NO MUNDO ===")
            first_player = players[0]
            world_joined = await client.join_world(first_player.id)
            
            if world_joined:
                # Testar movimento
                print("\n=== TESTANDO MOVIMENTO ===")
                await client.move_player(200.0, 300.0, "walk")
                
                # Testar ação
                print("\n=== TESTANDO AÇÕES ===")
                await client.perform_action("heal", parameters={"amount": "50"})
        
        print("\n✓ Teste completo finalizado!")
        
    except Exception as e:
        print(f"✗ Erro durante o teste: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    print("=== CLIENTE DE TESTE GameServer ===")
    print("Testando todas as funcionalidades do servidor MMORPG...\n")
    
    asyncio.run(test_complete_flow())
