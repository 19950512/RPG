import grpc
import threading
import os
from .Generated import auth_pb2_grpc, auth_pb2
from .Generated import player_pb2_grpc, player_pb2
import json, time, pathlib

TOKEN_STORE_PATH = pathlib.Path.home() / '.rpg_client_tokens.json'

class GrpcClient:
    def __init__(self, server_address=None):
        # Use environment variable or default port
        if server_address is None:
            port = os.getenv('GRPC_PORT', '5008')
            server_address = f'localhost:{port}'
        
        self.server_address = server_address
        self.channel = None
        self.auth_stub = None
        self.player_stub = None
        self._lock = threading.Lock()
        
        # Tokens
        self._jwt_token = None
        self._jwt_expires_at = 0
        self._refresh_token = None
        self._refresh_expires_at = 0

        self._load_tokens()

    @property
    def jwt_token(self):
        return self._jwt_token
    
    @jwt_token.setter
    def jwt_token(self, value):
        self._jwt_token = value

    def _save_tokens(self):
        with self._lock:
            try:
                data = {
                    'jwt_token': self._jwt_token,
                    'jwt_expires_at': self._jwt_expires_at,
                    'refresh_token': self._refresh_token,
                    'refresh_expires_at': self._refresh_expires_at,
                    'server': self.server_address
                }
                TOKEN_STORE_PATH.write_text(json.dumps(data))
            except Exception:
                pass

    def _load_tokens(self):
        with self._lock:
            try:
                if TOKEN_STORE_PATH.exists():
                    data = json.loads(TOKEN_STORE_PATH.read_text())
                    if data.get('server') == self.server_address:
                        self._jwt_token = data.get('jwt_token')
                        self._jwt_expires_at = data.get('jwt_expires_at', 0)
                        self._refresh_token = data.get('refresh_token')
                        self._refresh_expires_at = data.get('refresh_expires_at', 0)
            except Exception:
                pass

    def _clear_tokens(self):
        self._jwt_token = None
        self._jwt_expires_at = 0
        self._refresh_token = None
        self._refresh_expires_at = 0
        try:
            if TOKEN_STORE_PATH.exists():
                TOKEN_STORE_PATH.unlink()
        except Exception:
            pass

    def _is_jwt_valid(self):
        import time
        has_token = bool(self._jwt_token)
        time_valid = time.time() < (self._jwt_expires_at - 10)
        result = has_token and time_valid
        return result

    def _ensure_jwt(self):
        with self._lock:
            import time
            if self._is_jwt_valid():
                return self._jwt_token
            if self._refresh_token and time.time() < (self._refresh_expires_at - 30):
                # try refresh
                try:
                    print("🔄 Attempting token refresh...")
                    req = auth_pb2.RefreshTokenRequest(refresh_token=self._refresh_token)
                    resp = self.auth_stub.RefreshToken(req)
                    if resp.success:
                        print("✅ Token refresh successful")
                        self._jwt_token = resp.jwt_token
                        self._jwt_expires_at = resp.expires_at
                        self._refresh_token = resp.refresh_token
                        self._refresh_expires_at = resp.refresh_expires_at
                        self._save_tokens()
                        return self._jwt_token
                    else:
                        print(f"❌ Token refresh failed: {resp.message}")
                except Exception as e:
                    print(f"❌ Token refresh error: {e}")
                    pass
            print("❌ No valid JWT and cannot refresh; re-login required")
            raise RuntimeError("No valid JWT and cannot refresh; re-login required")

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
            # store tokens
            if response.success:
                import time
                self._jwt_token = response.jwt_token
                self._jwt_expires_at = response.expires_at
                self._refresh_token = response.refresh_token
                self._refresh_expires_at = response.refresh_expires_at
                self._save_tokens()
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
    
    def authenticated_metadata(self):
        import base64
        import json
        
        token = self._ensure_jwt()
        metadata = [('authorization', f'Bearer {token}')]
        
        # Extract account ID from JWT and add x-account-id header
        try:
            # JWT format: header.payload.signature
            # We need to decode the payload to get the account ID
            parts = token.split('.')
            if len(parts) == 3:
                # Decode the payload (add padding if needed)
                payload = parts[1]
                # Add padding for base64 decoding
                payload += '=' * (4 - len(payload) % 4)
                decoded_payload = base64.urlsafe_b64decode(payload)
                payload_data = json.loads(decoded_payload)
                
                # Extract account ID (could be in 'sub', 'nameid', or 'account_id')
                account_id = payload_data.get('sub') or payload_data.get('nameid') or payload_data.get('account_id')
                if account_id:
                    metadata.append(('x-account-id', account_id))
                    print(f"🔑 Added account ID header: {account_id}")
                else:
                    print("⚠️ No account ID found in JWT payload")
        except Exception as e:
            print(f"⚠️ Failed to extract account ID from JWT: {e}")
        
        return metadata

    def get_players(self, token=None):
        """Get list of characters for the authenticated user"""
        try:
            # Create the request
            request = player_pb2.ListCharactersRequest()
            
            # Create metadata with authorization token
            metadata = self.authenticated_metadata() if token is None else [('authorization', f'Bearer {token}')]
            
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
            metadata = self.authenticated_metadata() if token is None else [('authorization', f'Bearer {token}')]
            
            # Make the gRPC call
            response = self.player_stub.CreateCharacter(request, metadata=metadata)
            return response
            
        except grpc.RpcError as e:
            print(f"gRPC error in create_character: {e.code()} - {e.details()}")
            raise
        except Exception as e:
            print(f"Error in create_character: {e}")
            raise
    
    def join_world(self, token=None, player_id=None):
        """Join the game world with a character"""
        try:
            self._ensure_connection()
            
            # Create request
            request = player_pb2.JoinWorldRequest()
            if player_id:
                request.player_id = player_id
            
            # Add authorization header
            metadata = self.authenticated_metadata() if token is None else [('authorization', f'Bearer {token}')]
            
            # Make the gRPC call
            response = self.player_stub.JoinWorld(request, metadata=metadata)
            return response
            
        except grpc.RpcError as e:
            print(f"gRPC error in join_world: {e.code()} - {e.details()}")
            raise
        except Exception as e:
            print(f"Error in join_world: {e}")
            raise
    
    def leave_world(self, token=None):
        """Leave the game world"""
        try:
            self._ensure_connection()
            
            # Create request
            request = player_pb2.LeaveWorldRequest()
            
            # Add authorization header
            metadata = self.authenticated_metadata() if token is None else [('authorization', f'Bearer {token}')]
            
            # Make the gRPC call
            response = self.player_stub.LeaveWorld(request, metadata=metadata)
            return response
            
        except grpc.RpcError as e:
            print(f"gRPC error in leave_world: {e.code()} - {e.details()}")
            raise
        except Exception as e:
            print(f"Error in leave_world: {e}")
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
            metadata = self.authenticated_metadata() if token is None else [('authorization', f'Bearer {token}')]
            
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

    def logout(self):
        try:
            if not self._jwt_token and not self._refresh_token:
                self._clear_tokens()
                return True
            self._ensure_connection()
            if self.auth_stub:
                req = auth_pb2.LogoutRequest(jwt_token=self._jwt_token or '', refresh_token=self._refresh_token or '')
                try:
                    self.auth_stub.Logout(req, metadata=self.authenticated_metadata() if self._jwt_token else None)
                except Exception:
                    pass
            self._clear_tokens()
            return True
        except Exception:
            return False

# Global instance
grpc_client = GrpcClient()
