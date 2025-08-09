import grpc
import time
import random
from .Generated import world_pb2, world_pb2_grpc
from .grpc_client import grpc_client

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

    def _call_with_retry(self, func, request):
        """Executa RPC com retry único em caso de UNAUTHENTICATED tentando refresh automático."""
        metadata = grpc_client.authenticated_metadata()
        try:
            return func(request, metadata=metadata)
        except grpc.RpcError as e:
            if e.code() == grpc.StatusCode.UNAUTHENTICATED:
                # Em vez de invalidar o token, vamos forçar uma nova validação
                try:
                    # Force a new token check without invalidating
                    metadata = grpc_client.authenticated_metadata()
                    return func(request, metadata=metadata)
                except Exception:
                    raise
            raise

    def get_world_entities(self, _legacy_token_unused=None):
        """Get all world entities (NPCs, monsters, items)
        Parâmetro _legacy_token_unused mantido apenas por compatibilidade (ignorado)."""
        self._ensure_connection()
        request = world_pb2.GetWorldEntitiesRequest()
        return self._call_with_retry(self.world_stub.GetWorldEntities, request)

    def interact_with_entity(self, entity_id, interaction_type, parameters=None):
        """Interact with a world entity (attack, talk, pickup, etc.)"""
        self._ensure_connection()
        request = world_pb2.InteractWithEntityRequest(
            entity_id=entity_id,
            interaction_type=interaction_type
        )
        if parameters:
            for k, v in parameters.items():
                request.parameters[k] = str(v)
        return self._call_with_retry(self.world_stub.InteractWithEntity, request)

    def get_world_updates_stream(self, max_total_retries=None, on_reconnect=None):
        """Stream resiliente com reconexão automática e refresh de token.
        max_total_retries=None => infinito até consumidor parar.
        on_reconnect(callback) recebe dict com info do evento (ex: {'type':'unauthenticated'})."""
        self._ensure_connection()
        attempt = 0
        consecutive_errors = 0
        while True:
            if max_total_retries is not None and attempt > max_total_retries:
                break
            attempt += 1
            try:
                metadata = grpc_client.authenticated_metadata()
                request = world_pb2.WorldUpdateRequest()
                stream = self.world_stub.GetWorldUpdates(request, metadata=metadata)
                if on_reconnect and attempt > 1:
                    try:
                        on_reconnect({'type': 'reconnected', 'attempt': attempt})
                    except Exception:
                        pass
                # Reset error counters ao conectar
                consecutive_errors = 0
                for update in stream:
                    yield update
                # Se o loop do stream terminar naturalmente, tentamos reconectar após pequeno delay
                time.sleep(0.2)
            except grpc.RpcError as e:
                code = e.code()
                consecutive_errors += 1
                # Tratamento específico
                if code == grpc.StatusCode.UNAUTHENTICATED:
                    # forçar refresh e tentar novamente
                    if on_reconnect:
                        try: on_reconnect({'type': 'unauthenticated', 'attempt': attempt})
                        except Exception: pass
                    try:
                        # Em vez de invalidar o token, apenas force nova autenticação
                        grpc_client.authenticated_metadata()  # dispara refresh se necessário
                        # backoff curto antes de nova tentativa
                        time.sleep(0.25)
                        continue
                    except Exception:
                        if on_reconnect:
                            try: on_reconnect({'type': 'auth_failed'})
                            except Exception: pass
                        break
                elif code in (grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED, grpc.StatusCode.INTERNAL, grpc.StatusCode.CANCELLED):
                    if on_reconnect:
                        try: on_reconnect({'type': 'transient_error', 'code': code.name, 'attempt': attempt})
                        except Exception: pass
                    # Exponential backoff com jitter
                    backoff = min(5.0, (2 ** min(consecutive_errors, 5)) * 0.25)
                    backoff = backoff * (0.7 + random.random() * 0.6)
                    time.sleep(backoff)
                    continue
                else:
                    if on_reconnect:
                        try: on_reconnect({'type': 'fatal', 'code': code.name})
                        except Exception: pass
                    break
            except Exception:
                consecutive_errors += 1
                if on_reconnect:
                    try: on_reconnect({'type': 'exception', 'attempt': attempt})
                    except Exception: pass
                backoff = min(5.0, (2 ** min(consecutive_errors, 5)) * 0.25)
                time.sleep(backoff)
                continue

    def close(self):
        """Close the gRPC channel"""
        if self.channel:
            self.channel.close()
            self.channel = None
            self.world_stub = None

# Global instance
world_client = WorldClient()
