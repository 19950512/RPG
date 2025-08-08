import grpc
import threading
import sys
import os

# Adicionar o diretório Generated ao path para imports absolutos
current_dir = os.path.dirname(__file__)
generated_dir = os.path.join(current_dir, 'Generated')
sys.path.insert(0, generated_dir)

import auth_pb2_grpc, auth_pb2
import player_pb2_grpc, player_pb2

class GrpcClient:
    def __init__(self):
        self.server_address = 'localhost:5008'
        self.channel = None
        self.auth_stub = None
        self.player_stub = None
        self._lock = threading.Lock()
        
    def _ensure_connection(self):
        """Ensure we have an active gRPC connection"""
        with self._lock:
            if self.channel is None:
                try:
                    # Create channel with proper options for HTTP/2
                    options = [
                        ('grpc.keepalive_time_ms', 30000),
                        ('grpc.keepalive_timeout_ms', 5000),
                        ('grpc.keepalive_permit_without_calls', True),
                        ('grpc.http2.max_pings_without_data', 0),
                        ('grpc.http2.min_time_between_pings_ms', 10000),
                        ('grpc.http2.min_ping_interval_without_data_ms', 300000)
                    ]
                    
                    # Use insecure channel with HTTP/2 support
                    self.channel = grpc.insecure_channel(self.server_address, options=options)
                    
                    # Test the connection
                    grpc.channel_ready_future(self.channel).result(timeout=10)
                    print("Successfully connected to gRPC server")
                    
                    # Initialize stubs
                    self.auth_stub = auth_pb2_grpc.AuthServiceStub(self.channel)
                    self.player_stub = player_pb2_grpc.PlayerServiceStub(self.channel)
                    
                except grpc.FutureTimeoutError:
                    print("Timeout connecting to gRPC server")
                    if self.channel:
                        self.channel.close()
                        self.channel = None
                    raise ConnectionError("Failed to connect to gRPC server")
                except Exception as e:
                    print(f"Error connecting to gRPC server: {e}")
                    if self.channel:
                        self.channel.close()
                        self.channel = None
                    raise
    
    def connect(self):
        """Explicitly connect to the gRPC server"""
        self._ensure_connection()
    
    def register(self, email, password):
        """Register a new account"""
        try:
            self._ensure_connection()
            request = auth_pb2.RegisterRequest()
            request.email = email
            request.password = password
            response = self.auth_stub.Register(request)
            print(f"Register response: success={response.success}, message={response.message}")
            return response
        except grpc.RpcError as e:
            print(f"gRPC error in register: {e.code()} - {e.details()}")
            return None
        except Exception as e:
            print(f"Error in register: {e}")
            return None

    def login(self, email, password):
        """Login to get access token"""
        try:
            self._ensure_connection()
            request = auth_pb2.LoginRequest()
            request.email = email
            request.password = password
            response = self.auth_stub.Login(request)
            print(f"Login response: success={response.success}, message={response.message}")
            return response
        except grpc.RpcError as e:
            print(f"gRPC error in login: {e.code()} - {e.details()}")
            return None
        except Exception as e:
            print(f"Error in login: {e}")
            return None

    def create_character(self, token, name, vocation):
        """Create a new character"""
        try:
            self._ensure_connection()
            request = player_pb2.CreateCharacterRequest()
            request.name = name
            request.vocation = vocation
            
            # Add auth header
            metadata = [('authorization', f'Bearer {token}')]
            
            response = self.player_stub.CreateCharacter(request, metadata=metadata)
            print(f"Create character response: success={response.success}, message={response.message}")
            return response
        except grpc.RpcError as e:
            print(f"gRPC error in create_character: {e.code()} - {e.details()}")
            return None
        except Exception as e:
            print(f"Error in create_character: {e}")
            return None

    def list_characters(self, token):
        """List all characters for the account"""
        try:
            self._ensure_connection()
            request = player_pb2.ListCharactersRequest()
            
            # Add auth header
            metadata = [('authorization', f'Bearer {token}')]
            
            response = self.player_stub.ListCharacters(request, metadata=metadata)
            print(f"List characters response: success={response.success}, found {len(response.characters)} characters")
            return response
        except grpc.RpcError as e:
            print(f"gRPC error in list_characters: {e.code()} - {e.details()}")
            return None
        except Exception as e:
            print(f"Error in list_characters: {e}")
            return None

    def join_world(self, token):
        """Join the game world"""
        try:
            self._ensure_connection()
            request = player_pb2.JoinWorldRequest()
            
            # Add auth header
            metadata = [('authorization', f'Bearer {token}')]
            
            response = self.player_stub.JoinWorld(request, metadata=metadata)
            print(f"Join world response: success={response.success}, message={response.message}")
            return response
        except grpc.RpcError as e:
            print(f"gRPC error in join_world: {e.code()} - {e.details()}")
            return None
        except Exception as e:
            print(f"Error in join_world: {e}")
            return None

    def move_player(self, token, target_x, target_y, movement_type="walk"):
        """Move player to a target position"""
        try:
            self._ensure_connection()
            request = player_pb2.MovePlayerRequest()
            request.target_x = target_x
            request.target_y = target_y
            request.movement_type = movement_type
            
            # Add auth header
            metadata = [('authorization', f'Bearer {token}')]
            
            response = self.player_stub.MovePlayer(request, metadata=metadata)
            print(f"Move player response: success={response.success}, message={response.message}")
            return response
        except grpc.RpcError as e:
            print(f"gRPC error in move_player: {e.code()} - {e.details()}")
            return None
        except Exception as e:
            print(f"Error in move_player: {e}")
            raise

    def update_player_stats(self, token, level=None, experience=None, hp=None, mp=None):
        """Update player stats on server (using PerformAction as a workaround)"""
        try:
            self._ensure_connection()
            
            # For now, we'll use PerformAction to simulate stat updates
            # In a real implementation, you'd add a specific UpdatePlayerStats RPC
            request = player_pb2.PlayerActionRequest()
            request.action_type = "update_stats"
            
            # Use parameters to send the stats
            if level is not None:
                request.parameters["level"] = str(level)
            if experience is not None:
                request.parameters["experience"] = str(experience)
            if hp is not None:
                request.parameters["hp"] = str(hp)
            if mp is not None:
                request.parameters["mp"] = str(mp)
            
            # Add auth header
            metadata = [('authorization', f'Bearer {token}')]
            
            response = self.player_stub.PerformAction(request, metadata=metadata)
            print(f"Stats update sent to server: level={level}, exp={experience}")
            return response
            
        except grpc.RpcError as e:
            print(f"gRPC error in update_player_stats: {e.code()} - {e.details()}")
            return None
        except Exception as e:
            print(f"Error in update_player_stats: {e}")
            return None
    
    def update_player_position(self, token, position_x=None, position_y=None, facing_direction=None, movement_state=None):
        """Update player position and state on server (using PerformAction)"""
        try:
            self._ensure_connection()
            
            # Use PerformAction to update position and state
            request = player_pb2.PlayerActionRequest()
            request.action_type = "update_position"
            
            # Use parameters to send the position data
            if position_x is not None:
                request.parameters["position_x"] = str(position_x)
            if position_y is not None:
                request.parameters["position_y"] = str(position_y)
            if facing_direction is not None:
                request.parameters["facing_direction"] = str(facing_direction)
            if movement_state is not None:
                request.parameters["movement_state"] = str(movement_state)
            
            # Add auth header
            metadata = [('authorization', f'Bearer {token}')]
            
            response = self.player_stub.PerformAction(request, metadata=metadata)
            print(f"Position update sent to server: pos=({position_x},{position_y}), facing={facing_direction}, state={movement_state}")
            return response
            
        except grpc.RpcError as e:
            print(f"gRPC error in update_player_position: {e.code()} - {e.details()}")
            return None
        except Exception as e:
            print(f"Error in update_player_position: {e}")
            return None

    def close(self):
        """Close the gRPC connection"""
        if self.channel:
            self.channel.close()
            self.channel = None

# Global instance
grpc_client = GrpcClient()
