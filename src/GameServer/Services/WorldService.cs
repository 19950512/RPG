using System.Collections.Concurrent;
using GameServer.Data;
using GameServer.Models;
using Microsoft.EntityFrameworkCore;

namespace GameServer.Services;

public interface IWorldService
{
    Task<bool> JoinWorldAsync(Guid playerId);
    Task<bool> LeaveWorldAsync(Guid playerId);
    Task<bool> MovePlayerAsync(Guid playerId, float targetX, float targetY, string movementType);
    Task<bool> PerformPlayerActionAsync(Guid playerId, string actionType, Guid? targetId, Dictionary<string, string>? parameters);
    Task<Player?> GetPlayerAsync(Guid playerId);
    Task<IEnumerable<Player>> GetOnlinePlayersAsync();
    Task<bool> IsPositionValidAsync(float x, float y);
    Task<bool> IsPlayerOnlineAsync(Guid playerId);
    Task<bool> UpdatePlayerStateAsync(Player player);
    Task<IEnumerable<Player>> GetPlayersInRangeAsync(float x, float y, float range);
}

public class WorldService : IWorldService
{
    private readonly IServiceScopeFactory _scopeFactory;
    private readonly ILogger<WorldService> _logger;
    private readonly ConcurrentDictionary<Guid, Player> _onlinePlayers = new();
    private readonly Timer _updateTimer;

    public WorldService(IServiceScopeFactory scopeFactory, ILogger<WorldService> logger)
    {
        _scopeFactory = scopeFactory;
        _logger = logger;
        
        // Update player states every 1 second
        _updateTimer = new Timer(UpdatePlayerStates, null, TimeSpan.FromSeconds(1), TimeSpan.FromSeconds(1));
    }

    public async Task<Player?> GetPlayerAsync(Guid playerId)
    {
        if (_onlinePlayers.TryGetValue(playerId, out var onlinePlayer))
        {
            return onlinePlayer;
        }

        using var scope = _scopeFactory.CreateScope();
        var context = scope.ServiceProvider.GetRequiredService<GameDbContext>();
        
        return await context.Players.FirstOrDefaultAsync(p => p.Id == playerId);
    }

    public Task<IEnumerable<Player>> GetOnlinePlayersAsync()
    {
        return Task.FromResult(_onlinePlayers.Values.AsEnumerable());
    }

    public async Task<bool> JoinWorldAsync(Guid playerId)
    {
        try
        {
            using var scope = _scopeFactory.CreateScope();
            var context = scope.ServiceProvider.GetRequiredService<GameDbContext>();
            
            var player = await context.Players.FirstOrDefaultAsync(p => p.Id == playerId);
            if (player == null)
            {
                _logger.LogWarning("Player {PlayerId} not found", playerId);
                return false;
            }

            // Mark player as online
            player.IsOnline = true;
            player.LastUpdate = DateTime.UtcNow;
            
            await context.SaveChangesAsync();

            // Add to online players cache
            _onlinePlayers.TryAdd(playerId, player);

            _logger.LogInformation("Player {PlayerName} joined the world", player.Name);
            return true;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error joining world for player {PlayerId}", playerId);
            return false;
        }
    }

    public async Task<bool> LeaveWorldAsync(Guid playerId)
    {
        try
        {
            using var scope = _scopeFactory.CreateScope();
            var context = scope.ServiceProvider.GetRequiredService<GameDbContext>();
            
            var player = await context.Players.FirstOrDefaultAsync(p => p.Id == playerId);
            if (player != null)
            {
                player.IsOnline = false;
                player.LastUpdate = DateTime.UtcNow;
                await context.SaveChangesAsync();
            }

            // Remove from online players cache
            _onlinePlayers.TryRemove(playerId, out _);

            _logger.LogInformation("Player {PlayerId} left the world", playerId);
            return true;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error leaving world for player {PlayerId}", playerId);
            return false;
        }
    }

    public async Task<bool> MovePlayerAsync(Guid playerId, float targetX, float targetY, string movementType)
    {
        try
        {
            if (!await IsPositionValidAsync(targetX, targetY))
            {
                return false;
            }

            if (!_onlinePlayers.TryGetValue(playerId, out var player))
            {
                _logger.LogWarning("Player {PlayerId} not found in online players", playerId);
                return false;
            }

            // Validate movement speed (simple distance check)
            var deltaX = targetX - player.PositionX;
            var deltaY = targetY - player.PositionY;
            var distance = Math.Sqrt(deltaX * deltaX + deltaY * deltaY);

            // Maximum movement per tick based on speed
            var maxMovement = player.Speed * 0.1f; // Assuming 10 ticks per second
            
            if (distance > maxMovement)
            {
                // Normalize movement to max allowed distance
                var ratio = maxMovement / distance;
                targetX = player.PositionX + (float)(deltaX * ratio);
                targetY = player.PositionY + (float)(deltaY * ratio);
            }

            // Update player position
            player.PositionX = targetX;
            player.PositionY = targetY;
            player.MovementState = movementType;
            player.LastUpdate = DateTime.UtcNow;

            // Update facing direction based on movement
            if (Math.Abs(deltaX) > Math.Abs(deltaY))
            {
                player.FacingDirection = deltaX > 0 ? 3 : 1; // right : left
            }
            else if (Math.Abs(deltaY) > 0.1f)
            {
                player.FacingDirection = deltaY > 0 ? 0 : 2; // down : up
            }

            // Save to database periodically (not every movement)
            using var scope = _scopeFactory.CreateScope();
            var context = scope.ServiceProvider.GetRequiredService<GameDbContext>();
            
            context.Players.Update(player);
            await context.SaveChangesAsync();

            return true;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error moving player {PlayerId}", playerId);
            return false;
        }
    }

    public async Task<bool> PerformPlayerActionAsync(Guid playerId, string actionType, Guid? targetId, Dictionary<string, string>? parameters)
    {
        try
        {
            if (!_onlinePlayers.TryGetValue(playerId, out var player))
            {
                return false;
            }

            switch (actionType.ToLower())
            {
                case "attack":
                    return await HandleAttackAction(player, targetId);
                case "heal":
                    return await HandleHealAction(player);
                case "chat":
                    return await HandleChatAction(player, parameters);
                default:
                    _logger.LogWarning("Unknown action type: {ActionType}", actionType);
                    return false;
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error performing action {ActionType} for player {PlayerId}", actionType, playerId);
            return false;
        }
    }

    public Task<bool> IsPositionValidAsync(float x, float y)
    {
        // Simple bounds checking - adjust based on your world size
        const float minX = 0;
        const float maxX = 1000;
        const float minY = 0;
        const float maxY = 1000;

        var isValid = x >= minX && x <= maxX && y >= minY && y <= maxY;
        return Task.FromResult(isValid);
    }

    public Task<bool> IsPlayerOnlineAsync(Guid playerId)
    {
        return Task.FromResult(_onlinePlayers.ContainsKey(playerId));
    }

    public Task<bool> UpdatePlayerStateAsync(Player player)
    {
        try
        {
            if (_onlinePlayers.TryGetValue(player.Id, out var existingPlayer))
            {
                // Update the cached player
                existingPlayer.PositionX = player.PositionX;
                existingPlayer.PositionY = player.PositionY;
                existingPlayer.CurrentHp = player.CurrentHp;
                existingPlayer.CurrentMp = player.CurrentMp;
                existingPlayer.MovementState = player.MovementState;
                existingPlayer.FacingDirection = player.FacingDirection;
                existingPlayer.LastUpdate = DateTime.UtcNow;
                
                return Task.FromResult(true);
            }
            
            return Task.FromResult(false);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error updating player state for {PlayerId}", player.Id);
            return Task.FromResult(false);
        }
    }

    public Task<IEnumerable<Player>> GetPlayersInRangeAsync(float x, float y, float range)
    {
        var playersInRange = _onlinePlayers.Values
            .Where(p =>
            {
                var deltaX = p.PositionX - x;
                var deltaY = p.PositionY - y;
                var distance = Math.Sqrt(deltaX * deltaX + deltaY * deltaY);
                return distance <= range;
            })
            .ToList();

        return Task.FromResult(playersInRange.AsEnumerable());
    }

    private async void UpdatePlayerStates(object? state)
    {
        try
        {
            if (_onlinePlayers.IsEmpty) return;

            using var scope = _scopeFactory.CreateScope();
            var context = scope.ServiceProvider.GetRequiredService<GameDbContext>();

            // Save all online player states to database
            foreach (var player in _onlinePlayers.Values.ToList())
            {
                context.Players.Update(player);
            }

            await context.SaveChangesAsync();
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error updating player states");
        }
    }

    private Task<bool> HandleAttackAction(Player attacker, Guid? targetId)
    {
        if (targetId == null || !_onlinePlayers.TryGetValue(targetId.Value, out var target))
        {
            return Task.FromResult(false);
        }

        // Check if target is in range (simple distance check)
        var deltaX = target.PositionX - attacker.PositionX;
        var deltaY = target.PositionY - attacker.PositionY;
        var distance = Math.Sqrt(deltaX * deltaX + deltaY * deltaY);

        if (distance > 50) // Attack range
        {
            return Task.FromResult(false);
        }

        // Calculate damage
        var damage = Math.Max(1, attacker.Attack - target.Defense);
        target.CurrentHp = Math.Max(0, target.CurrentHp - damage);

        _logger.LogInformation("Player {AttackerName} attacked {TargetName} for {Damage} damage",
            attacker.Name, target.Name, damage);

        return Task.FromResult(true);
    }

    private Task<bool> HandleHealAction(Player player)
    {
        if (player.CurrentMp < 10) // Mana cost for heal
        {
            return Task.FromResult(false);
        }

        player.CurrentMp -= 10;
        player.CurrentHp = Math.Min(player.MaxHp, player.CurrentHp + 20);

        _logger.LogInformation("Player {PlayerName} healed", player.Name);
        return Task.FromResult(true);
    }

    private Task<bool> HandleChatAction(Player player, Dictionary<string, string>? parameters)
    {
        if (parameters?.TryGetValue("message", out var message) == true)
        {
            _logger.LogInformation("Player {PlayerName} says: {Message}", player.Name, message);
            return Task.FromResult(true);
        }

        return Task.FromResult(false);
    }

    public void Dispose()
    {
        _updateTimer?.Dispose();
    }
}