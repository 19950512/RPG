import grpc
import threading
from .Generated import auth_pb2_grpc, auth_pb2
from .Generated import player_pb2_grpc, player_pb2

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
    
    def login(self, email, password):
        """Login with email and password"""
        try:
            self._ensure_connection()
            if self.auth_stub is None:
                raise Exception("Auth service not available")
                
            request = auth_pb2.LoginRequest(email=email, password=password)
            print(f"Sending login request for: {email}")
            response = self.auth_stub.Login(request)
            print("Login response received successfully")
            return response
        except grpc.RpcError as e:
            print(f"gRPC error during login: {e.code()}: {e.details()}")
            raise
        except Exception as e:
            print(f"Unexpected error during login: {e}")
            raise
    
    def create_account(self, email, password):
        """Create a new account"""
        try:
            self._ensure_connection()
            if self.auth_stub is None:
                raise Exception("Auth service not available")
                
            request = auth_pb2.CreateAccountRequest(email=email, password=password)
            print(f"Sending create account request for: {email}")
            response = self.auth_stub.CreateAccount(request)
            print("Create account response received successfully")
            return response
        except grpc.RpcError as e:
            print(f"gRPC error during account creation: {e.code()}: {e.details()}")
            raise
        except Exception as e:
            print(f"Unexpected error during account creation: {e}")
            raise
    
    def get_players(self, token):
        """Get list of characters for the authenticated user"""
        try:
            # Create the request
            request = player_pb2.ListCharactersRequest()
            
            # Create metadata with authorization token
            metadata = [('authorization', f'Bearer {token}')]
            
            # Make the gRPC call
            response = self.player_stub.ListCharacters(request, metadata=metadata)
            return response
            
        except grpc.RpcError as e:
            print(f"gRPC error in get_players: {e.code()} - {e.details()}")
            raise
        except Exception as e:
            print(f"Error in get_players: {e}")
            raise
    
    def create_character(self, token, name, vocation):
        """Create a new character for the authenticated user"""
        try:
            # Create the request
            request = player_pb2.CreateCharacterRequest()
            request.name = name
            request.vocation = vocation
            
            # Create metadata with authorization token
            metadata = [('authorization', f'Bearer {token}')]
            
            # Make the gRPC call
            response = self.player_stub.CreateCharacter(request, metadata=metadata)
            return response
            
        except grpc.RpcError as e:
            print(f"gRPC error in create_character: {e.code()} - {e.details()}")
            raise
        except Exception as e:
            print(f"Error in create_character: {e}")
            raise
    
    def join_world(self, token, player_id=None):
        """Join the game world with a character"""
        try:
            self._ensure_connection()
            
            # Create request
            request = player_pb2.JoinWorldRequest()
            if player_id:
                request.player_id = player_id
            
            # Add authorization header
            metadata = [('authorization', f'Bearer {token}')]
            
            # Make the gRPC call
            response = self.player_stub.JoinWorld(request, metadata=metadata)
            return response
            
        except grpc.RpcError as e:
            print(f"gRPC error in join_world: {e.code()} - {e.details()}")
            raise
        except Exception as e:
            print(f"Error in join_world: {e}")
            raise
    
    def move_player(self, token, target_x, target_y, movement_type="walk"):
        """Move player to a target position"""
        try:
            self._ensure_connection()
            
            # Create request
            request = player_pb2.PlayerMoveRequest(
                target_x=float(target_x),
                target_y=float(target_y),
                movement_type=movement_type
            )
            
            # Add authorization header
            metadata = [('authorization', f'Bearer {token}')]
            
            # Make the gRPC call
            response = self.player_stub.MovePlayer(request, metadata=metadata)
            return response
            
        except grpc.RpcError as e:
            print(f"gRPC error in move_player: {e.code()} - {e.details()}")
            raise
        except Exception as e:
            print(f"Error in move_player: {e}")
            raise
    
    def update_player_stats(self, token, level=None, experience=None, hp=None, mp=None):
        """Update player stats on server (using PerformAction as a workaround)"""
        try:
            if not self.channel:
                self.connect()
            
            # For now, we'll use PerformAction to simulate stat updates
            # In a real implementation, you'd add a specific UpdatePlayerStats RPC
            request = player_pb2.PlayerActionRequest()
            request.action_type = "update_player_stats"
            
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
            if response and response.success:
                print(f"✅ Stats update sent to server: level={level}, exp={experience}")
            else:
                print(f"❌ Stats update failed: {response.message if response else 'No response'}")
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
            if not self.channel:
                self.connect()
            
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
            if response and response.success:
                print(f"✅ Position update sent to server: pos=({position_x},{position_y}), facing={facing_direction}, state={movement_state}")
            else:
                print(f"❌ Position update failed: {response.message if response else 'No response'}")
            return response
            
        except grpc.RpcError as e:
            print(f"gRPC error in update_player_position: {e.code()} - {e.details()}")
            return None
        except Exception as e:
            print(f"Error in update_player_position: {e}")
            return None
    
    def get_world_state(self, auth_token):
        """Get current world state from server (polling-based)"""
        try:
            self._ensure_connection()
            
            # Prepare metadata with auth token
            metadata = [('authorization', f'Bearer {auth_token}')]
            
            # Create request
            request = player_pb2.GetWorldStateRequest()
            
            # Make the call
            response = self.player_stub.GetWorldState(request, metadata=metadata)
            
            print(f"🌍 Received world state with {len(response.players)} players")
            return response
                
        except grpc.RpcError as e:
            print(f"gRPC error in get_world_state: {e.code()} - {e.details()}")
            return None
        except Exception as e:
            print(f"Error in get_world_state: {e}")
            return None

    def get_world_updates(self, auth_token):
        """Get streaming world updates from server"""
        try:
            self._ensure_connection()
            
            # Prepare metadata with auth token
            metadata = [('authorization', f'Bearer {auth_token}')]
            
            # Create request
            request = player_pb2.WorldUpdateRequest()
            
            # Get streaming response
            response_iterator = self.player_stub.GetWorldUpdates(request, metadata=metadata)
            
            print("🌍 Started receiving world updates stream")
            
            # Yield each update
            for response in response_iterator:
                yield response
                
        except grpc.RpcError as e:
            print(f"gRPC error in get_world_updates: {e.code()} - {e.details()}")
            return
        except Exception as e:
            print(f"Error in get_world_updates: {e}")
            return
    
    def close(self):
        """Close the gRPC connection"""
        if self.channel:
            self.channel.close()
            self.channel = None

# Global instance
grpc_client = GrpcClient()
