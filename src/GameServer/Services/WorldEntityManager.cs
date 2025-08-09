using System.Collections.Concurrent;
using System.Threading.Channels;
using Microsoft.EntityFrameworkCore;
using GameServer.Data;
using GameServer.Models;
using System.Text.Json;

namespace GameServer.Services;

public interface IWorldEntityManager
{
    Task<IEnumerable<WorldEntity>> GetAllEntitiesAsync();
    Task<WorldEntity?> GetEntityAsync(Guid entityId);
    Task<WorldEntity> CreateEntityAsync(WorldEntity entity);
    Task<WorldEntity> UpdateEntityAsync(WorldEntity entity);
    Task<bool> RemoveEntityAsync(Guid entityId);
    Task BroadcastEntityUpdateAsync(WorldEntity entity);
    Task ScheduleRespawnAsync(WorldEntity entity);
    Task InitializeDefaultEntitiesAsync(); // (opcional, manter caso queira usar em testes)
    
    // Streaming updates
    Channel<List<EntityUpdate>> SubscribeToUpdates();
    void UnsubscribeFromUpdates(Channel<List<EntityUpdate>> channel);
}

public class WorldEntityManager : IWorldEntityManager, IDisposable
{
    private readonly IServiceScopeFactory _scopeFactory;
    private readonly ILogger<WorldEntityManager> _logger;
    private readonly ConcurrentDictionary<Guid, WorldEntity> _entities = new();
    private readonly List<Channel<List<EntityUpdate>>> _updateSubscribers = new();
    private readonly Timer _respawnTimer;
    private readonly Timer _broadcastTimer;
    private readonly ConcurrentQueue<EntityUpdate> _pendingUpdates = new();
    private readonly SemaphoreSlim _loadSemaphore = new(1,1);

    public WorldEntityManager(IServiceScopeFactory scopeFactory, ILogger<WorldEntityManager> logger)
    {
        _scopeFactory = scopeFactory;
        _logger = logger;
        
        _logger.LogInformation("🌍 WorldEntityManager inicializando...");
        
        // Initialize timers
        _respawnTimer = new Timer(state => Task.Run(() => ProcessRespawns(state)), null, TimeSpan.FromSeconds(30), TimeSpan.FromSeconds(30));
        _broadcastTimer = new Timer(state => Task.Run(() => ProcessBroadcasts(state)), null, TimeSpan.FromSeconds(1), TimeSpan.FromSeconds(1));
        
        // Load entities from database (fire and forget, mas poderemos forçar depois)
        _logger.LogInformation("🌍 Iniciando carregamento de entidades do banco...");
        _ = Task.Run(async () => await LoadEntitiesFromDatabase(null));
    }

    public Task<IEnumerable<WorldEntity>> GetAllEntitiesAsync()
    {
        var list = _entities.Values.Where(e => e.EntityType != "monster" || e.IsAlive);
        _logger.LogInformation("🌍 GetAllEntitiesAsync chamado - retornando {Count} entidades (cache total: {CacheTotal})", 
            list.Count(), _entities.Count);
        return Task.FromResult(list);
    }

    public Task<WorldEntity?> GetEntityAsync(Guid entityId)
    {
        _entities.TryGetValue(entityId, out var entity);
        return Task.FromResult(entity);
    }

    public async Task<WorldEntity> CreateEntityAsync(WorldEntity entity)
    {
        using var scope = _scopeFactory.CreateScope();
        var context = scope.ServiceProvider.GetRequiredService<GameDbContext>();
        
        context.WorldEntities.Add(entity);
        await context.SaveChangesAsync();
        
        _entities[entity.Id] = entity;
        
        // Broadcast new entity
        _pendingUpdates.Enqueue(new EntityUpdate
        {
            EntityId = entity.Id,
            Entity = entity,
            IsRemoved = false
        });
        
        _logger.LogInformation("Created new entity: {EntityName} ({EntityType}) at ({X}, {Y})", 
            entity.Name, entity.EntityType, entity.PositionX, entity.PositionY);
        
        return entity;
    }

    public async Task<WorldEntity> UpdateEntityAsync(WorldEntity entity)
    {
        using var scope = _scopeFactory.CreateScope();
        var context = scope.ServiceProvider.GetRequiredService<GameDbContext>();
        
        entity.LastUpdate = DateTime.UtcNow;
        context.WorldEntities.Update(entity);
        await context.SaveChangesAsync();
        
        _entities[entity.Id] = entity;
        
        return entity;
    }

    public async Task<bool> RemoveEntityAsync(Guid entityId)
    {
        using var scope = _scopeFactory.CreateScope();
        var context = scope.ServiceProvider.GetRequiredService<GameDbContext>();
        
        var entity = await context.WorldEntities.FindAsync(entityId);
        if (entity != null)
        {
            context.WorldEntities.Remove(entity);
            await context.SaveChangesAsync();
            
            _entities.TryRemove(entityId, out _);
            
            // Broadcast removal
            _pendingUpdates.Enqueue(new EntityUpdate
            {
                EntityId = entityId,
                Entity = null,
                IsRemoved = true
            });
            
            _logger.LogInformation("Removed entity: {EntityId}", entityId);
            return true;
        }
        
        return false;
    }

    public Task BroadcastEntityUpdateAsync(WorldEntity entity)
    {
        _pendingUpdates.Enqueue(new EntityUpdate
        {
            EntityId = entity.Id,
            Entity = entity,
            IsRemoved = false
        });
        return Task.CompletedTask;
    }

    public Task ScheduleRespawnAsync(WorldEntity entity)
    {
        if (entity.EntityType == "monster" && entity.RespawnDelaySeconds > 0)
        {
            _logger.LogInformation("Scheduled respawn for {EntityName} in {RespawnDelay} seconds", 
                entity.Name, entity.RespawnDelaySeconds);
        }
        return Task.CompletedTask;
    }

    public async Task InitializeDefaultEntitiesAsync()
    {
        using var scope = _scopeFactory.CreateScope();
        var context = scope.ServiceProvider.GetRequiredService<GameDbContext>();
        
        // Check if entities already exist
        var existingCount = await context.WorldEntities.CountAsync();
        if (existingCount > 0)
        {
            _logger.LogInformation("World entities already initialized ({Count} entities)", existingCount);
            return;
        }
        
        _logger.LogInformation("Initializing default world entities...");
        
        var entities = new List<WorldEntity>();
        
        // Create some NPCs
        entities.Add(new WorldEntity
        {
            Name = "Village Elder",
            EntityType = "npc",
            PositionX = 500,
            PositionY = 500,
            SpawnX = 500,
            SpawnY = 500,
            CurrentHp = 100,
            MaxHp = 100,
            Attack = 0,
            Defense = 10,
            Properties = JsonSerializer.Serialize(new Dictionary<string, string>
            {
                ["dialog"] = "Welcome to our village, traveler! Beware of the monsters to the north."
            })
        });
        
        entities.Add(new WorldEntity
        {
            Name = "Merchant",
            EntityType = "npc",
            PositionX = 600,
            PositionY = 500,
            SpawnX = 600,
            SpawnY = 500,
            CurrentHp = 80,
            MaxHp = 80,
            Attack = 0,
            Defense = 5,
            Properties = JsonSerializer.Serialize(new Dictionary<string, string>
            {
                ["dialog"] = "I sell the finest weapons and armor! Come back when you have gold."
            })
        });
        
        // Create some monsters
        for (int i = 0; i < 5; i++)
        {
            var x = 400 + (i * 100);
            var y = 300;
            
            entities.Add(new WorldEntity
            {
                Name = $"Orc Warrior {i + 1}",
                EntityType = "monster",
                PositionX = x,
                PositionY = y,
                SpawnX = x,
                SpawnY = y,
                CurrentHp = 50,
                MaxHp = 50,
                CurrentMp = 0,
                MaxMp = 0,
                Attack = 12,
                Defense = 3,
                Speed = 1.0f,
                RespawnDelaySeconds = 300, // 5 minutes
                Properties = JsonSerializer.Serialize(new Dictionary<string, string>
                {
                    ["type"] = "orc",
                    ["aggressive"] = "true"
                })
            });
        }
        
        // Create some stronger monsters
        for (int i = 0; i < 3; i++)
        {
            var x = 300 + (i * 150);
            var y = 200;
            
            entities.Add(new WorldEntity
            {
                Name = $"Troll {i + 1}",
                EntityType = "monster",
                PositionX = x,
                PositionY = y,
                SpawnX = x,
                SpawnY = y,
                CurrentHp = 100,
                MaxHp = 100,
                CurrentMp = 20,
                MaxMp = 20,
                Attack = 20,
                Defense = 8,
                Speed = 0.8f,
                RespawnDelaySeconds = 600, // 10 minutes
                Properties = JsonSerializer.Serialize(new Dictionary<string, string>
                {
                    ["type"] = "troll",
                    ["aggressive"] = "true"
                })
            });
        }
        
        // Create some items
        entities.Add(new WorldEntity
        {
            Name = "Health Potion",
            EntityType = "item",
            PositionX = 550,
            PositionY = 450,
            SpawnX = 550,
            SpawnY = 450,
            Properties = JsonSerializer.Serialize(new Dictionary<string, string>
            {
                ["type"] = "consumable",
                ["effect"] = "heal",
                ["value"] = "25"
            })
        });
        
        // Save to database
        context.WorldEntities.AddRange(entities);
        await context.SaveChangesAsync();
        
        // Add to memory
        foreach (var entity in entities)
        {
            _entities[entity.Id] = entity;
        }
        
        _logger.LogInformation("Initialized {Count} default world entities", entities.Count);
    }

    public Channel<List<EntityUpdate>> SubscribeToUpdates()
    {
        var channel = Channel.CreateUnbounded<List<EntityUpdate>>();
        lock (_updateSubscribers)
        {
            _updateSubscribers.Add(channel);
        }
        return channel;
    }

    public void UnsubscribeFromUpdates(Channel<List<EntityUpdate>> channel)
    {
        lock (_updateSubscribers)
        {
            _updateSubscribers.Remove(channel);
        }
    }

    private async Task LoadEntitiesFromDatabase(object? state)
    {
        if (!await _loadSemaphore.WaitAsync(TimeSpan.FromSeconds(5)))
        {
            _logger.LogWarning("🌍 Não foi possível obter lock para carregar entidades (já em andamento).");
            return;
        }
        try
        {
            _logger.LogInformation("🌍 Conectando ao banco para carregar entidades...");
            using var scope = _scopeFactory.CreateScope();
            var context = scope.ServiceProvider.GetRequiredService<GameDbContext>();
            
            _logger.LogInformation("🌍 Consultando WorldEntities no banco...");
            var entities = await context.WorldEntities.ToListAsync();
            
            _logger.LogInformation("🌍 Encontradas {Count} entidades no banco", entities.Count);
            
            foreach (var entity in entities)
            {
                _entities[entity.Id] = entity;
                _logger.LogDebug("🌍 Carregada entidade: {Name} ({Type}) em ({X},{Y})", 
                    entity.Name, entity.EntityType, entity.PositionX, entity.PositionY);
            }
            
            _logger.LogInformation("🌍 ✅ Loaded {Count} entities from database (cache total={CacheCount})", entities.Count, _entities.Count);
            
            if (_entities.IsEmpty)
            {
                _logger.LogWarning("🌍 ⚠️ Cache de entidades está vazio após carregamento!");
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "🌍 ❌ Error loading entities from database");
        }
        finally
        {
            _loadSemaphore.Release();
        }
    }

    private async void ProcessRespawns(object? state)
    {
        try
        {
            var now = DateTime.UtcNow;
            var entitiesToRespawn = _entities.Values
                .Where(e => !e.IsAlive && 
                           e.EntityType == "monster" && 
                           e.DeathTime.HasValue &&
                           (now - e.DeathTime.Value).TotalSeconds >= e.RespawnDelaySeconds)
                .ToList();
            
            foreach (var entity in entitiesToRespawn)
            {
                // Respawn the monster
                entity.IsAlive = true;
                entity.CurrentHp = entity.MaxHp;
                entity.CurrentMp = entity.MaxMp;
                entity.PositionX = entity.SpawnX;
                entity.PositionY = entity.SpawnY;
                entity.DeathTime = null;
                entity.LastUpdate = now;
                
                await UpdateEntityAsync(entity);
                await BroadcastEntityUpdateAsync(entity);
                
                _logger.LogInformation("Respawned monster: {EntityName} at ({X}, {Y})", 
                    entity.Name, entity.PositionX, entity.PositionY);
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error processing respawns");
        }
    }

    private void ProcessBroadcasts(object? state)
    {
        try
        {
            if (_pendingUpdates.IsEmpty)
                return;
                
            var updates = new List<EntityUpdate>();
            while (_pendingUpdates.TryDequeue(out var update))
            {
                updates.Add(update);
            }
            
            if (updates.Count == 0)
                return;
            
            lock (_updateSubscribers)
            {
                foreach (var subscriber in _updateSubscribers.ToList())
                {
                    try
                    {
                        if (!subscriber.Writer.TryWrite(updates))
                        {
                            // Channel is closed, remove it
                            _updateSubscribers.Remove(subscriber);
                        }
                    }
                    catch (Exception ex)
                    {
                        _logger.LogWarning(ex, "Error broadcasting to subscriber");
                        _updateSubscribers.Remove(subscriber);
                    }
                }
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error processing broadcasts");
        }
    }

    public void Dispose()
    {
        _respawnTimer?.Dispose();
        _broadcastTimer?.Dispose();
        
        lock (_updateSubscribers)
        {
            foreach (var subscriber in _updateSubscribers)
            {
                subscriber.Writer.Complete();
            }
            _updateSubscribers.Clear();
        }
    }
}

public class EntityUpdate
{
    public Guid EntityId { get; set; }
    public WorldEntity? Entity { get; set; }
    public bool IsRemoved { get; set; }
}
