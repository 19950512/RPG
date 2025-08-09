using Grpc.Core;
using Microsoft.EntityFrameworkCore;
using System.Collections.Concurrent;
using System.Security.Claims;
using System.Text.Json;
using System.Threading.Channels;
using GameServer.Data;
using GameServer.Models;
using GameServer.Protos;
using ProtoWorldEntity = GameServer.Protos.WorldEntity;
using ModelWorldEntity = GameServer.Models.WorldEntity;

namespace GameServer.Services;

public class WorldServiceImpl : WorldService.WorldServiceBase
{
    private readonly IServiceScopeFactory _scopeFactory;
    private readonly ILogger<WorldServiceImpl> _logger;
    private readonly IWorldEntityManager _worldEntityManager;

    public WorldServiceImpl(
        IServiceScopeFactory scopeFactory,
        ILogger<WorldServiceImpl> logger,
        IWorldEntityManager worldEntityManager)
    {
        _scopeFactory = scopeFactory;
        _logger = logger;
        _worldEntityManager = worldEntityManager;
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

    public override async Task<GetWorldEntitiesResponse> GetWorldEntities(
        GetWorldEntitiesRequest request, 
        ServerCallContext context)
    {
        try
        {
            // Auth (ensures interceptor set header)
            _ = GetAccountId(context);

            // Ensure cache loaded (only if empty)
            await _worldEntityManager.ForceReloadAsync();

            var entities = await _worldEntityManager.GetAllEntitiesAsync();
            var response = new GetWorldEntitiesResponse
            {
                Timestamp = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()
            };

            foreach (var entity in entities)
            {
                if (!entity.IsAlive && entity.EntityType == "monster") continue; // filter dead monsters
                var type = (entity.EntityType ?? string.Empty).Trim().ToLowerInvariant();
                var worldEntity = MapToProtoWorldEntity(entity);
                switch (type)
                {
                    case "npc":
                        response.Npcs.Add(worldEntity); break;
                    case "monster":
                        response.Monsters.Add(worldEntity); break;
                    case "item":
                        response.Items.Add(worldEntity); break;
                    default:
                        _logger.LogWarning("Entity {Id} unexpected type='{Type}'", entity.Id, entity.EntityType);
                        break;
                }
            }

            _logger.LogDebug("Returned {NpcCount} NPCs, {MonsterCount} monsters, {ItemCount} items",
                response.Npcs.Count, response.Monsters.Count, response.Items.Count);

            return response;
        }
        catch (Exception ex) when (ex is not RpcException)
        {
            _logger.LogError(ex, "Error getting world entities");
            throw new RpcException(new Status(StatusCode.Internal, "Failed to get world entities"));
        }
    }

    public override async Task<InteractWithEntityResponse> InteractWithEntity(
        InteractWithEntityRequest request,
        ServerCallContext context)
    {
        try
        {
            var accountId = GetAccountId(context);
            _logger.LogInformation("Player {AccountId} interacting with entity {EntityId} - {InteractionType}",
                accountId, request.EntityId, request.InteractionType);

            using var scope = _scopeFactory.CreateScope();
            var dbContext = scope.ServiceProvider.GetRequiredService<GameDbContext>();

            var player = await dbContext.Players.FirstOrDefaultAsync(p => p.AccountId == accountId && p.IsOnline);
            if (player == null)
            {
                throw new RpcException(new Status(StatusCode.NotFound, "Player not found or offline"));
            }

            if (!Guid.TryParse(request.EntityId, out var entityId))
            {
                throw new RpcException(new Status(StatusCode.InvalidArgument, "Invalid entity ID"));
            }

            var entity = await _worldEntityManager.GetEntityAsync(entityId);
            if (entity == null)
            {
                return new InteractWithEntityResponse { Success = false, Message = "Entity not found" };
            }

            var result = await ProcessInteraction(player, entity, request.InteractionType, request.Parameters);

            if (result.EntityModified)
            {
                await _worldEntityManager.UpdateEntityAsync(entity);
                await _worldEntityManager.BroadcastEntityUpdateAsync(entity);
            }

            var response = new InteractWithEntityResponse
            {
                Success = result.Success,
                Message = result.Message
            };

            if (result.EntityModified)
            {
                response.AffectedEntities.Add(MapToProtoWorldEntity(entity));
            }
            foreach (var reward in result.Rewards)
            {
                response.Rewards[reward.Key] = reward.Value;
            }
            return response;
        }
        catch (RpcException)
        {
            throw;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error processing entity interaction");
            throw new RpcException(new Status(StatusCode.Internal, "Failed to process interaction"));
        }
    }

    public override async Task GetWorldUpdates(
        WorldUpdateRequest request,
        IServerStreamWriter<WorldUpdateResponse> responseStream,
        ServerCallContext context)
    {
        try
        {
            var accountId = GetAccountId(context);
            _logger.LogInformation("Starting world updates stream for player account {AccountId}", accountId);

            var updateQueue = _worldEntityManager.SubscribeToUpdates();

            try
            {
                while (!context.CancellationToken.IsCancellationRequested)
                {
                    var cancellationTokenSource = CancellationTokenSource.CreateLinkedTokenSource(context.CancellationToken);
                    cancellationTokenSource.CancelAfter(TimeSpan.FromSeconds(30));
                    try
                    {
                        var updates = await updateQueue.Reader.ReadAsync(cancellationTokenSource.Token);
                        var response = new WorldUpdateResponse { Timestamp = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() };
                        foreach (var update in updates)
                        {
                            if (update.IsRemoved)
                                response.RemovedEntityIds.Add(update.EntityId.ToString());
                            else if (update.Entity != null)
                                response.UpdatedEntities.Add(MapToProtoWorldEntity(update.Entity));
                        }
                        if (response.UpdatedEntities.Count > 0 || response.RemovedEntityIds.Count > 0)
                        {
                            await responseStream.WriteAsync(response);
                        }
                    }
                    catch (OperationCanceledException) when (!context.CancellationToken.IsCancellationRequested)
                    {
                        await responseStream.WriteAsync(new WorldUpdateResponse { Timestamp = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() });
                    }
                }
            }
            finally
            {
                _worldEntityManager.UnsubscribeFromUpdates(updateQueue);
            }
        }
        catch (RpcException)
        {
            throw;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error in world updates stream");
            throw new RpcException(new Status(StatusCode.Internal, "World updates stream error"));
        }
    }

    private async Task<InteractionResult> ProcessInteraction(
        Player player,
        ModelWorldEntity entity,
        string interactionType,
        IDictionary<string, string> parameters)
    {
        switch (interactionType.ToLower())
        {
            case "attack":
                return await ProcessAttack(player, entity, parameters);
            case "talk":
                return ProcessTalk(player, entity);
            case "pickup":
                return await ProcessPickup(player, entity);
            default:
                return new InteractionResult
                {
                    Success = false,
                    Message = $"Unknown interaction type: {interactionType}"
                };
        }
    }

    private async Task<InteractionResult> ProcessAttack(
        Player player,
        ModelWorldEntity entity,
        IDictionary<string, string> parameters)
    {
        if (entity.EntityType != "monster")
        {
            return new InteractionResult
            {
                Success = false,
                Message = "You can only attack monsters"
            };
        }

        if (!entity.IsAlive)
        {
            return new InteractionResult
            {
                Success = false,
                Message = "This monster is already dead"
            };
        }

        // Calculate distance
        var distance = Math.Sqrt(Math.Pow(player.PositionX - entity.PositionX, 2) + 
                                Math.Pow(player.PositionY - entity.PositionY, 2));
        
        if (distance > 64) // Attack range
        {
            return new InteractionResult
            {
                Success = false,
                Message = "Target is too far away"
            };
        }

        // Calculate damage
        var playerAttack = player.Attack;
        var monsterDefense = entity.Defense;
        var damage = Math.Max(1, playerAttack - monsterDefense);

        // Apply damage
        entity.CurrentHp = Math.Max(0, entity.CurrentHp - damage);
        entity.LastUpdate = DateTime.UtcNow;

        var result = new InteractionResult
        {
            Success = true,
            EntityModified = true,
            Message = $"You attack {entity.Name} for {damage} damage!"
        };

        // Check if monster died
        if (entity.CurrentHp <= 0)
        {
            entity.IsAlive = false;
            entity.DeathTime = DateTime.UtcNow;
            result.Message += $" {entity.Name} has been defeated!";

            // Give experience and potentially items
            var expGained = CalculateExperience(entity);
            result.Rewards["experience"] = expGained.ToString();
            result.Message += $" You gained {expGained} experience!";

            // Schedule respawn
            await _worldEntityManager.ScheduleRespawnAsync(entity);
        }

        return result;
    }

    private InteractionResult ProcessTalk(Player player, ModelWorldEntity entity)
    {
        if (entity.EntityType != "npc")
        {
            return new InteractionResult
            {
                Success = false,
                Message = "You can only talk to NPCs"
            };
        }

        // Parse properties for dialog
        var properties = JsonSerializer.Deserialize<Dictionary<string, object>>(entity.Properties) ?? new();
        var dialog = properties.GetValueOrDefault("dialog", $"Hello, I am {entity.Name}!").ToString();

        return new InteractionResult
        {
            Success = true,
            Message = $"{entity.Name}: {dialog}"
        };
    }

    private async Task<InteractionResult> ProcessPickup(Player player, ModelWorldEntity entity)
    {
        if (entity.EntityType != "item")
        {
            return new InteractionResult
            {
                Success = false,
                Message = "You can only pickup items"
            };
        }

        // Calculate distance
        var distance = Math.Sqrt(Math.Pow(player.PositionX - entity.PositionX, 2) + 
                                Math.Pow(player.PositionY - entity.PositionY, 2));
        
        if (distance > 32) // Pickup range
        {
            return new InteractionResult
            {
                Success = false,
                Message = "Item is too far away"
            };
        }

        // Remove item from world (mark for removal)
        await _worldEntityManager.RemoveEntityAsync(entity.Id);

        return new InteractionResult
        {
            Success = true,
            Message = $"You picked up {entity.Name}!",
            EntityModified = true // Will trigger removal broadcast
        };
    }

    private int CalculateExperience(ModelWorldEntity monster)
    {
        // Base experience calculation
        var baseExp = 10;
        var levelMultiplier = Math.Max(1, monster.MaxHp / 20); // Roughly based on HP
        return baseExp * levelMultiplier;
    }

    private Protos.WorldEntity MapToProtoWorldEntity(Models.WorldEntity entity)
    {
        var protoEntity = new Protos.WorldEntity
        {
            Id = entity.Id.ToString(),
            Name = entity.Name,
            EntityType = entity.EntityType,
            PositionX = entity.PositionX,
            PositionY = entity.PositionY,
            CurrentHp = entity.CurrentHp,
            MaxHp = entity.MaxHp,
            CurrentMp = entity.CurrentMp,
            MaxMp = entity.MaxMp,
            Attack = entity.Attack,
            Defense = entity.Defense,
            Speed = entity.Speed,
            MovementState = entity.MovementState,
            FacingDirection = entity.FacingDirection,
            IsAlive = entity.IsAlive
        };

        // Parse and add properties
        try
        {
            var properties = JsonSerializer.Deserialize<Dictionary<string, string>>(entity.Properties) ?? new();
            foreach (var prop in properties)
            {
                protoEntity.Properties[prop.Key] = prop.Value;
            }
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Failed to parse properties for entity {EntityId}", entity.Id);
        }

        return protoEntity;
    }
}

public class InteractionResult
{
    public bool Success { get; set; }
    public string Message { get; set; } = string.Empty;
    public bool EntityModified { get; set; }
    public Dictionary<string, string> Rewards { get; set; } = new();
}
