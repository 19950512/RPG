import grpc
import threading
from .Protos import auth_pb2_grpc, auth_pb2
from .Protos import player_pb2_grpc, player_pb2

class GrpcClient:
    def __init__(self):
        self.server_address = 'localhost:5001'
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
    
    def close(self):
        """Close the gRPC connection"""
        if self.channel:
            self.channel.close()
            self.channel = None

# Global instance
grpc_client = GrpcClient()
