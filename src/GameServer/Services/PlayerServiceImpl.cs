using Grpc.Core;
using Microsoft.EntityFrameworkCore;
using GameServer.Data;
using GameServer.Models;
using GameServer.Protos;
using System.Collections.Concurrent;

namespace GameServer.Services;

public class PlayerServiceImpl : GameServer.Protos.PlayerService.PlayerServiceBase
{
    private readonly GameDbContext _dbContext;
    private readonly ILogger<PlayerServiceImpl> _logger;
    private readonly IWorldManager _worldService;
    private readonly ConcurrentDictionary<string, IServerStreamWriter<WorldUpdateResponse>> _worldStreams = new();
    private readonly ItemService _itemService; // novo

    public PlayerServiceImpl(GameDbContext dbContext, ILogger<PlayerServiceImpl> logger, IWorldManager worldService, ItemService itemService)
    {
        _dbContext = dbContext;
        _logger = logger;
        _worldService = worldService;
        _itemService = itemService;
    }

    private Guid GetAccountId(ServerCallContext context)
    {
        var header = context.RequestHeaders.FirstOrDefault(h => h.Key == "x-account-id")?.Value;
        if (header == null || !Guid.TryParse(header, out var accountId))
        {
            throw new RpcException(new Status(StatusCode.Unauthenticated, "Missing or invalid account id header"));
        }
        return accountId;
    }

    public override async Task<CreateCharacterResponse> CreateCharacter(CreateCharacterRequest request, ServerCallContext context)
    {
        try
        {
            var accountId = GetAccountId(context);

            // Validate input
            if (string.IsNullOrWhiteSpace(request.Name) || string.IsNullOrWhiteSpace(request.Vocation))
            {
                return new CreateCharacterResponse
                {
                    Success = false,
                    Message = "Character name and vocation are required"
                };
            }

            if (request.Name.Length < 3 || request.Name.Length > 50)
            {
                return new CreateCharacterResponse
                {
                    Success = false,
                    Message = "Character name must be between 3 and 50 characters"
                };
            }

            var validVocations = new[] { "Knight", "Paladin", "Mage", "Assassin" };
            if (!validVocations.Contains(request.Vocation))
            {
                return new CreateCharacterResponse
                {
                    Success = false,
                    Message = $"Invalid vocation. Valid options: {string.Join(", ", validVocations)}"
                };
            }

            // Check if character name is already taken
            var existingPlayer = await _dbContext.Players
                .FirstOrDefaultAsync(p => p.Name.ToLower() == request.Name.ToLower());

            if (existingPlayer != null)
            {
                return new CreateCharacterResponse
                {
                    Success = false,
                    Message = "Character name already taken"
                };
            }

            // Verify account exists
            var account = await _dbContext.Accounts
                .FirstOrDefaultAsync(a => a.Id == accountId && a.IsActive);

            if (account == null)
            {
                throw new RpcException(new Status(StatusCode.NotFound, "Account not found"));
            }

            // Create new character
            var player = new Player
            {
                AccountId = accountId,
                Name = request.Name,
                Vocation = request.Vocation,
                Experience = 0,
                Level = 1
            };

            _dbContext.Players.Add(player);
            await _dbContext.SaveChangesAsync();

            _logger.LogInformation("Character created: {Name} ({Vocation}) for account {AccountId}", 
                request.Name, request.Vocation, accountId);

            var playerInfo = new PlayerInfo
            {
                Id = player.Id.ToString(),
                Name = player.Name,
                Vocation = player.Vocation,
                Experience = player.Experience,
                Level = player.Level
            };

            return new CreateCharacterResponse
            {
                Success = true,
                Message = "Character created successfully",
                Player = playerInfo
            };
        }
        catch (RpcException)
        {
            throw;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error creating character");
            return new CreateCharacterResponse
            {
                Success = false,
                Message = "Internal server error"
            };
        }
    }

    public override async Task<ListCharactersResponse> ListCharacters(ListCharactersRequest request, ServerCallContext context)
    {
        try
        {
            var accountId = GetAccountId(context);

            // Get all characters for this account
            var players = await _dbContext.Players
                .Where(p => p.AccountId == accountId)
                .Select(p => new PlayerInfo
                {
                    Id = p.Id.ToString(),
                    Name = p.Name,
                    Vocation = p.Vocation,
                    Experience = p.Experience,
                    Level = p.Level,
                    PositionX = p.PositionX,
                    PositionY = p.PositionY,
                    CurrentHp = p.CurrentHp,
                    MaxHp = p.MaxHp,
                    CurrentMp = p.CurrentMp,
                    MaxMp = p.MaxMp,
                    Attack = p.Attack,
                    Defense = p.Defense,
                    Speed = p.Speed,
                    MovementState = p.MovementState,
                    FacingDirection = p.FacingDirection,
                    IsOnline = p.IsOnline
                })
                .ToListAsync();

            _logger.LogInformation("Listed {Count} characters for account {AccountId}", players.Count, accountId);

            var response = new ListCharactersResponse();
            response.Players.AddRange(players);

            return response;
        }
        catch (RpcException)
        {
            throw;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error listing characters");
            throw new RpcException(new Status(StatusCode.Internal, "Internal server error"));
        }
    }

    public override async Task<JoinWorldResponse> JoinWorld(JoinWorldRequest request, ServerCallContext context)
    {
        _logger.LogInformation("[JoinWorld] START requestPlayerId={RequestPlayerId}", string.IsNullOrWhiteSpace(request.PlayerId) ? "<none>" : request.PlayerId);
        Guid accountId;
        try
        {
            accountId = GetAccountId(context);
        }
        catch (RpcException rex)
        {
            _logger.LogWarning(rex, "[JoinWorld] Auth/Account header error");
            throw; // Propaga para o cliente como UNAUTHENTICATED
        }

        try
        {
            _logger.LogDebug("[JoinWorld] Account resolved accountId={AccountId}", accountId);
            Player? player = null;

            if (!string.IsNullOrEmpty(request.PlayerId) && Guid.TryParse(request.PlayerId, out var requestedPlayerGuid))
            {
                _logger.LogDebug("[JoinWorld] Looking for specific playerId={PlayerId}", requestedPlayerGuid);
                player = await _dbContext.Players.FirstOrDefaultAsync(p => p.Id == requestedPlayerGuid && p.AccountId == accountId);
                if (player == null)
                {
                    _logger.LogWarning("[JoinWorld] Player {PlayerId} not found or not owned by account {AccountId}", requestedPlayerGuid, accountId);
                    return new JoinWorldResponse { Success = false, Message = "Player not found or doesn't belong to your account" };
                }
            }
            else
            {
                _logger.LogDebug("[JoinWorld] No specific playerId provided. Fetching first character for account {AccountId}", accountId);
                player = await _dbContext.Players.Where(p => p.AccountId == accountId).FirstOrDefaultAsync();
                if (player == null)
                {
                    _logger.LogWarning("[JoinWorld] No characters found for account {AccountId}", accountId);
                    return new JoinWorldResponse { Success = false, Message = "No characters found. Create a character first." };
                }
            }

            _logger.LogDebug("[JoinWorld] Found player {PlayerName} ({PlayerId}) IsOnline={IsOnline} Pos=({X},{Y})", player.Name, player.Id, player.IsOnline, player.PositionX, player.PositionY);

            // Atualiza estado do player
            player.IsOnline = true;
            player.LastUpdate = DateTime.UtcNow;
            _logger.LogDebug("[JoinWorld] Marking player online and saving changes...");
            await _dbContext.SaveChangesAsync();
            _logger.LogDebug("[JoinWorld] Player saved successfully");

            // Registra no world manager
            _logger.LogDebug("[JoinWorld] Registering player in WorldManager cache...");
            var worldAdded = await _worldService.JoinWorldAsync(player.Id);
            if (!worldAdded)
            {
                _logger.LogError("[JoinWorld] Failed to add player {PlayerId} to WorldManager cache", player.Id);
                return new JoinWorldResponse { Success = false, Message = "Failed to join world (world cache)" };
            }
            _logger.LogInformation("[JoinWorld] Player ONLINE {PlayerName} ({PlayerId}) at ({X},{Y})", player.Name, player.Id, player.PositionX, player.PositionY);

            // Buscar outros players
            var otherPlayers = await _dbContext.Players
                .Where(p => p.IsOnline && p.Id != player.Id)
                .Take(10)
                .Select(p => new PlayerInfo
                {
                    Id = p.Id.ToString(),
                    Name = p.Name,
                    Vocation = p.Vocation,
                    Level = p.Level,
                    PositionX = p.PositionX,
                    PositionY = p.PositionY,
                    CurrentHp = p.CurrentHp,
                    MaxHp = p.MaxHp,
                    CurrentMp = p.CurrentMp,
                    MaxMp = p.MaxMp,
                    Attack = p.Attack,
                    Defense = p.Defense,
                    Speed = p.Speed,
                    MovementState = p.MovementState,
                    FacingDirection = p.FacingDirection,
                    IsOnline = p.IsOnline
                })
                .ToListAsync();

            _logger.LogDebug("[JoinWorld] OtherPlayersCount={Count}", otherPlayers.Count);

            return new JoinWorldResponse
            {
                Success = true,
                Message = $"Welcome to the world, {player.Name}! {otherPlayers.Count} other players online.",
                Player = new PlayerInfo
                {
                    Id = player.Id.ToString(),
                    Name = player.Name,
                    Vocation = player.Vocation,
                    Experience = player.Experience,
                    Level = player.Level,
                    PositionX = player.PositionX,
                    PositionY = player.PositionY,
                    CurrentHp = player.CurrentHp,
                    MaxHp = player.MaxHp,
                    CurrentMp = player.CurrentMp,
                    MaxMp = player.MaxMp,
                    Attack = player.Attack,
                    Defense = player.Defense,
                    Speed = player.Speed,
                    MovementState = player.MovementState,
                    FacingDirection = player.FacingDirection,
                    IsOnline = player.IsOnline
                },
                OtherPlayers = { otherPlayers }
            };
        }
        catch (RpcException)
        {
            throw; // deixa interceptor/pipeline lidar
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "[JoinWorld] Unexpected error account={AccountId} requestPlayerId={RequestPlayerId}", accountId, request.PlayerId);
            return new JoinWorldResponse { Success = false, Message = "Failed to join world" };
        }
    }

    public override async Task<LeaveWorldResponse> LeaveWorld(LeaveWorldRequest request, ServerCallContext context)
    {
        try
        {
            var accountId = GetAccountId(context);

            _logger.LogInformation($"🚪 Player leaving world for account: {accountId}");

            // Buscar o player online
            var player = await _dbContext.Players
                .FirstOrDefaultAsync(p => p.AccountId == accountId && p.IsOnline);

            if (player == null)
            {
                return new LeaveWorldResponse
                {
                    Success = false,
                    Message = "Player not found or already offline"
                };
            }

            // Colocar o player offline
            player.IsOnline = false;
            player.LastUpdate = DateTime.UtcNow;
            await _dbContext.SaveChangesAsync();

            // Remove player from WorldService cache
            await _worldService.LeaveWorldAsync(player.Id);

            _logger.LogInformation($"🚪✅ Player {player.Name} ({player.Id}) is now OFFLINE");

            return new LeaveWorldResponse
            {
                Success = true,
                Message = $"Goodbye, {player.Name}! You have left the world safely."
            };
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error leaving world");
            return new LeaveWorldResponse
            {
                Success = false,
                Message = "Failed to leave world"
            };
        }
    }

    public override async Task<PlayerMoveResponse> MovePlayer(PlayerMoveRequest request, ServerCallContext context)
    {
        try
        {
            var accountId = GetAccountId(context);

            _logger.LogInformation($"🔥 Movement request for account {accountId}: ({request.TargetX}, {request.TargetY}) - {request.MovementType}");

            // Buscar o player online
            var player = await _dbContext.Players
                .FirstOrDefaultAsync(p => p.AccountId == accountId && p.IsOnline);

            if (player == null)
            {
                return new PlayerMoveResponse
                {
                    Success = false,
                    Message = "Player not found or not online. Use JoinWorld first."
                };
            }

            // Validações de movimento
            if (request.TargetX < 0 || request.TargetY < 0)
            {
                return new PlayerMoveResponse
                {
                    Success = false,
                    Message = "Invalid target position: coordinates must be positive"
                };
            }

            // Calcular distância para validar se o movimento é possível
            var currentX = player.PositionX;
            var currentY = player.PositionY;
            var distance = Math.Sqrt(Math.Pow(request.TargetX - currentX, 2) + Math.Pow(request.TargetY - currentY, 2));
            
            // Velocidade baseada no tipo de movimento
            var maxMoveDistance = request.MovementType?.ToLower() == "run" ? player.Speed * 2 : player.Speed;
            
            // Para este exemplo, vamos permitir qualquer movimento (sem validação de distância máxima)
            // Em um jogo real, você validaria se o movimento é possível baseado na velocidade
            _logger.LogInformation($"🔥 Moving {player.Name} from ({currentX}, {currentY}) to ({request.TargetX}, {request.TargetY}) - Distance: {distance:F2}");

            // Determinar direção do movimento para atualizar FacingDirection
            var deltaX = request.TargetX - currentX;
            var deltaY = request.TargetY - currentY;
            int facingDirection = 0; // 0=North, 1=East, 2=South, 3=West
            
            if (Math.Abs(deltaX) > Math.Abs(deltaY))
            {
                facingDirection = deltaX > 0 ? 1 : 3; // East : West
            }
            else
            {
                facingDirection = deltaY > 0 ? 2 : 0; // South : North
            }

            // Atualizar posição no banco de dados
            player.PositionX = request.TargetX;
            player.PositionY = request.TargetY;
            player.FacingDirection = facingDirection;
            player.MovementState = request.MovementType ?? "walk";
            player.LastUpdate = DateTime.UtcNow;

            await _dbContext.SaveChangesAsync();

            _logger.LogInformation($"🔥✅ Movement completed! {player.Name} is now at ({player.PositionX}, {player.PositionY}) facing {facingDirection}");

            return new PlayerMoveResponse
            {
                Success = true,
                Message = $"Moved to ({request.TargetX}, {request.TargetY})"
            };
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error moving player");
            return new PlayerMoveResponse
            {
                Success = false,
                Message = "Failed to move player"
            };
        }
    }

    public override async Task<PlayerActionResponse> PerformAction(PlayerActionRequest request, ServerCallContext context)
    {
        try
        {
            var accountId = GetAccountId(context);

            var player = await _dbContext.Players
                .FirstOrDefaultAsync(p => p.AccountId == accountId && p.IsOnline);

            if (player == null)
            {
                return new PlayerActionResponse
                {
                    Success = false,
                    Message = "Player not found or not online"
                };
            }

            Guid? targetId = null;
            if (!string.IsNullOrEmpty(request.TargetId) && Guid.TryParse(request.TargetId, out var parsedTargetId))
            {
                targetId = parsedTargetId;
            }

            var parameters = request.Parameters?.ToDictionary(kvp => kvp.Key, kvp => kvp.Value);

            var success = await _worldService.PerformPlayerActionAsync(player.Id, request.ActionType, targetId, parameters);

            var response = new PlayerActionResponse
            {
                Success = success,
                Message = success ? "Action performed successfully" : "Failed to perform action"
            };

            // Get affected players for response
            if (success)
            {
                var affectedPlayers = await _worldService.GetPlayersInRangeAsync(player.PositionX, player.PositionY, 100);
                foreach (var affectedPlayer in affectedPlayers)
                {
                    response.AffectedPlayers.Add(ConvertToPlayerInfo(affectedPlayer));
                }
            }

            return response;
        }
        catch (RpcException)
        {
            throw;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error performing action");
            throw new RpcException(new Status(StatusCode.Internal, "Internal server error"));
        }
    }

    public override async Task<GetWorldStateResponse> GetWorldState(GetWorldStateRequest request, ServerCallContext context)
    {
        var accountId = GetAccountId(context);

        _logger.LogInformation("🌍 Getting world state for account {AccountId}", accountId);

        var onlinePlayers = await _worldService.GetOnlinePlayersAsync();
        
        var response = new GetWorldStateResponse
        {
            Timestamp = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()
        };

        foreach (var player in onlinePlayers)
        {
            response.Players.Add(ConvertToPlayerInfo(player));
        }

        _logger.LogInformation("🎯 Returning world state with {PlayerCount} players", response.Players.Count);
        return response;
    }

    public override async Task<PickUpItemResponse> PickUpItem(PickUpItemRequest request, ServerCallContext context)
    {
        try
        {
            var accountId = GetAccountId(context);
            if (!Guid.TryParse(request.PlayerId, out var playerId))
            {
                return new PickUpItemResponse { Success = false, Message = "Invalid player id" };
            }

            Guid? itemIdGuid = null;
            if (!string.IsNullOrEmpty(request.ItemId) && Guid.TryParse(request.ItemId, out var parsedItemId))
            {
                itemIdGuid = parsedItemId;
            }

            // Fallback 1: se não veio item_id válido mas veio world_entity_id, tentar resolver
            if (itemIdGuid == null && !string.IsNullOrEmpty(request.WorldEntityId) && Guid.TryParse(request.WorldEntityId, out var worldEntityGuid))
            {
                var resolved = await _itemService.ResolveWorldEntityItemAsync(worldEntityGuid);
                if (resolved != null)
                {
                    itemIdGuid = resolved.Value;
                    _logger.LogDebug("[PickUpItem] Resolvido via world_entity_id direto: {WorldEntityId} -> {ItemId}", worldEntityGuid, itemIdGuid);
                }
                else
                {
                    return new PickUpItemResponse { Success = false, Message = "WorldEntity sem item associado" };
                }
            }

            // Fallback 2 (melhoria): se veio item_id mas NÃO existe item com esse Id, pode ser que o cliente tenha enviado o WorldEntityId no campo item_id.
            if (itemIdGuid != null)
            {
                bool exists = await _dbContext.Items.AnyAsync(i => i.Id == itemIdGuid.Value);
                if (!exists)
                {
                    // Tentar interpretar itemIdGuid como world entity id
                    var possibleEntity = await _dbContext.WorldEntities.FirstOrDefaultAsync(w => w.Id == itemIdGuid.Value);
                    if (possibleEntity?.ItemId != null)
                    {
                        _logger.LogInformation("[PickUpItem] Interpretado item_id={Original} como world_entity_id; resolvido ItemId={Resolved}", itemIdGuid, possibleEntity.ItemId);
                        itemIdGuid = possibleEntity.ItemId;
                    }
                    else if (!string.IsNullOrEmpty(request.WorldEntityId) && Guid.TryParse(request.WorldEntityId, out var weFromRequest))
                    {
                        // Última tentativa: usar explicitamente world_entity_id fornecido
                        var entityExplicit = await _dbContext.WorldEntities.FirstOrDefaultAsync(w => w.Id == weFromRequest);
                        if (entityExplicit?.ItemId != null)
                        {
                            _logger.LogInformation("[PickUpItem] Usou world_entity_id explícito após item inexistente: {WorldEntityId} -> {ItemId}", weFromRequest, entityExplicit.ItemId);
                            itemIdGuid = entityExplicit.ItemId;
                        }
                        else
                        {
                            return new PickUpItemResponse { Success = false, Message = "Item não encontrado (fallback)" };
                        }
                    }
                    else
                    {
                        return new PickUpItemResponse { Success = false, Message = "Invalid item id" };
                    }
                }
            }

            if (itemIdGuid == null)
            {
                return new PickUpItemResponse { Success = false, Message = "Invalid item id" };
            }

            var player = await _dbContext.Players.FirstOrDefaultAsync(p => p.Id == playerId && p.AccountId == accountId);
            if (player == null)
            {
                return new PickUpItemResponse { Success = false, Message = "Player not found for this account" };
            }

            var (success, reason) = await _itemService.TryPickUpItemAsync(playerId, itemIdGuid.Value);
            return new PickUpItemResponse
            {
                Success = success,
                Message = reason
            };
        }
        catch (RpcException)
        {
            throw;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error picking up item");
            throw new RpcException(new Status(StatusCode.Internal, "Error picking up item"));
        }
    }

    public override async Task<ResolveWorldEntityItemResponse> ResolveWorldEntityItem(ResolveWorldEntityItemRequest request, ServerCallContext context)
    {
        try
        {
            if (!Guid.TryParse(request.WorldEntityId, out var worldEntityGuid))
            {
                return new ResolveWorldEntityItemResponse { Success = false, Message = "Invalid world entity id" };
            }
            var itemId = await _itemService.ResolveWorldEntityItemAsync(worldEntityGuid);
            if (itemId == null)
            {
                return new ResolveWorldEntityItemResponse { Success = false, Message = "No item for world entity" };
            }
            return new ResolveWorldEntityItemResponse { Success = true, Message = "Resolved", ItemId = itemId.Value.ToString() };
        }
        catch (RpcException)
        {
            throw;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error resolving world entity item");
            throw new RpcException(new Status(StatusCode.Internal, "Error resolving world entity item"));
        }
    }

    private static PlayerInfo ConvertToPlayerInfo(Player player)
    {
        return new PlayerInfo
        {
            Id = player.Id.ToString(),
            Name = player.Name,
            Vocation = player.Vocation,
            Experience = player.Experience,
            Level = player.Level,
            PositionX = player.PositionX,
            PositionY = player.PositionY,
            CurrentHp = player.CurrentHp,
            MaxHp = player.MaxHp,
            CurrentMp = player.CurrentMp,
            MaxMp = player.MaxMp,
            Attack = player.Attack,
            Defense = player.Defense,
            Speed = player.Speed,
            MovementState = player.MovementState,
            FacingDirection = player.FacingDirection,
            IsOnline = player.IsOnline
        };
    }
}
