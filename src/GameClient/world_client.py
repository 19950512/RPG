import grpc
from .Generated import world_pb2, world_pb2_grpc

class WorldClient:
    def __init__(self, server_address="localhost:5008"):
        self.server_address = server_address
        self.channel = None
        self.world_stub = None
        
    def _ensure_connection(self):
        """Ensure gRPC connection is established"""
        if self.channel is None:
            self.channel = grpc.insecure_channel(self.server_address)
            self.world_stub = world_pb2_grpc.WorldServiceStub(self.channel)
            
    def get_world_entities(self, token=None):
        """Get all world entities (NPCs, monsters, items)"""
        try:
            self._ensure_connection()
            
            request = world_pb2.GetWorldEntitiesRequest()
            
            # Try without authorization first (for testing)
            try:
                response = self.world_stub.GetWorldEntities(request)
                return response
            except grpc.RpcError as e:
                # If unauthorized, try with token
                if e.code() == grpc.StatusCode.UNAUTHENTICATED and token:
                    metadata = [('authorization', f'Bearer {token}')]
                    response = self.world_stub.GetWorldEntities(request, metadata=metadata)
                    return response
                else:
                    raise
            
        except grpc.RpcError as e:
            print(f"gRPC error in get_world_entities: {e.code()} - {e.details()}")
            raise
        except Exception as e:
            print(f"Error in get_world_entities: {e}")
            raise
            
    def interact_with_entity(self, token, entity_id, interaction_type, parameters=None):
        """Interact with a world entity (attack, talk, pickup, etc.)"""
        try:
            self._ensure_connection()
            
            request = world_pb2.InteractWithEntityRequest()
            request.entity_id = entity_id
            request.interaction_type = interaction_type
            
            if parameters:
                for key, value in parameters.items():
                    request.parameters[key] = str(value)
            
            # Try without authorization first (for testing)
            try:
                response = self.world_stub.InteractWithEntity(request)
                return response
            except grpc.RpcError as e:
                # If unauthorized, try with token
                if e.code() == grpc.StatusCode.UNAUTHENTICATED and token:
                    metadata = [('authorization', f'Bearer {token}')]
                    response = self.world_stub.InteractWithEntity(request, metadata=metadata)
                    return response
                else:
                    raise
            
        except grpc.RpcError as e:
            print(f"gRPC error in interact_with_entity: {e.code()} - {e.details()}")
            raise
        except Exception as e:
            print(f"Error in interact_with_entity: {e}")
            raise
            
    def get_world_updates_stream(self, token):
        """Get real-time world updates stream"""
        try:
            self._ensure_connection()
            
            request = world_pb2.WorldUpdateRequest()
            metadata = [('authorization', f'Bearer {token}')]
            
            # Return the stream generator
            return self.world_stub.GetWorldUpdates(request, metadata=metadata)
            
        except grpc.RpcError as e:
            print(f"gRPC error in get_world_updates_stream: {e.code()} - {e.details()}")
            raise
        except Exception as e:
            print(f"Error in get_world_updates_stream: {e}")
            raise
            
    def close(self):
        """Close the gRPC channel"""
        if self.channel:
            self.channel.close()
            self.channel = None
            self.world_stub = None

# Global instance
world_client = WorldClient()
