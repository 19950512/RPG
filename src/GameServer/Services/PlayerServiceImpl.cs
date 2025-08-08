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
    private readonly IWorldService _worldService;
    private readonly ConcurrentDictionary<string, IServerStreamWriter<WorldUpdateResponse>> _worldStreams = new();

    public PlayerServiceImpl(GameDbContext dbContext, ILogger<PlayerServiceImpl> logger, IWorldService worldService)
    {
        _dbContext = dbContext;
        _logger = logger;
        _worldService = worldService;
    }

    public override async Task<CreateCharacterResponse> CreateCharacter(CreateCharacterRequest request, ServerCallContext context)
    {
        try
        {
            // Get account ID from context (added by JWT interceptor)
            var accountIdHeader = context.RequestHeaders.FirstOrDefault(h => h.Key == "x-account-id");
            if (accountIdHeader == null || !Guid.TryParse(accountIdHeader.Value, out var accountId))
            {
                throw new RpcException(new Status(StatusCode.Unauthenticated, "Invalid account context"));
            }

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
            // Get account ID from context (added by JWT interceptor)
            var accountIdHeader = context.RequestHeaders.FirstOrDefault(h => h.Key == "x-account-id");
            if (accountIdHeader == null || !Guid.TryParse(accountIdHeader.Value, out var accountId))
            {
                throw new RpcException(new Status(StatusCode.Unauthenticated, "Invalid account context"));
            }

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
        try
        {
            // Get account ID from context (added by JWT interceptor)
            var accountIdHeader = context.RequestHeaders.FirstOrDefault(h => h.Key == "x-account-id");
            if (accountIdHeader == null || !Guid.TryParse(accountIdHeader.Value, out var accountId))
            {
                throw new RpcException(new Status(StatusCode.Unauthenticated, "Invalid account context"));
            }

            _logger.LogInformation($"🌍 Player joining world for account: {accountId}");

            // Se player_id foi fornecido, usar esse específico, senão pegar o primeiro da conta
            Player? player;
            if (!string.IsNullOrEmpty(request.PlayerId) && Guid.TryParse(request.PlayerId, out var playerId))
            {
                player = await _dbContext.Players
                    .FirstOrDefaultAsync(p => p.Id == playerId && p.AccountId == accountId);
                
                if (player == null)
                {
                    return new JoinWorldResponse
                    {
                        Success = false,
                        Message = "Player not found or doesn't belong to your account"
                    };
                }
            }
            else
            {
                // Pegar o primeiro personagem da conta
                player = await _dbContext.Players
                    .Where(p => p.AccountId == accountId)
                    .FirstOrDefaultAsync();
                
                if (player == null)
                {
                    return new JoinWorldResponse
                    {
                        Success = false,
                        Message = "No characters found. Create a character first."
                    };
                }
            }

            // Colocar o player online
            player.IsOnline = true;
            player.LastUpdate = DateTime.UtcNow;
            await _dbContext.SaveChangesAsync();

            _logger.LogInformation($"🌍 Player {player.Name} ({player.Id}) is now ONLINE at position ({player.PositionX}, {player.PositionY})");

            // Buscar outros players online (opcional - para mostrar quem está no mundo)
            var otherPlayers = await _dbContext.Players
                .Where(p => p.IsOnline && p.Id != player.Id)
                .Take(10) // Limitar para não sobrecarregar
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
                    IsOnline = p.IsOnline
                })
                .ToListAsync();

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
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error joining world");
            return new JoinWorldResponse
            {
                Success = false,
                Message = "Failed to join world"
            };
        }
    }

    public override async Task<PlayerMoveResponse> MovePlayer(PlayerMoveRequest request, ServerCallContext context)
    {
        try
        {
            // Get account ID from context (added by JWT interceptor)
            var accountIdHeader = context.RequestHeaders.FirstOrDefault(h => h.Key == "x-account-id");
            if (accountIdHeader == null || !Guid.TryParse(accountIdHeader.Value, out var accountId))
            {
                throw new RpcException(new Status(StatusCode.Unauthenticated, "Invalid account context"));
            }

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
            var accountIdHeader = context.RequestHeaders.FirstOrDefault(h => h.Key == "x-account-id");
            if (accountIdHeader == null || !Guid.TryParse(accountIdHeader.Value, out var accountId))
            {
                throw new RpcException(new Status(StatusCode.Unauthenticated, "Invalid account context"));
            }

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

    public override async Task GetWorldUpdates(WorldUpdateRequest request, IServerStreamWriter<WorldUpdateResponse> responseStream, ServerCallContext context)
    {
        var accountIdHeader = context.RequestHeaders.FirstOrDefault(h => h.Key == "x-account-id");
        if (accountIdHeader == null || !Guid.TryParse(accountIdHeader.Value, out var accountId))
        {
            throw new RpcException(new Status(StatusCode.Unauthenticated, "Invalid account context"));
        }

        var streamId = Guid.NewGuid().ToString();
        _worldStreams.TryAdd(streamId, responseStream);

        try
        {
            _logger.LogInformation("Started world updates stream for account {AccountId}", accountId);

            // Send updates every 100ms
            while (!context.CancellationToken.IsCancellationRequested)
            {
                var onlinePlayers = await _worldService.GetOnlinePlayersAsync();
                
                var response = new WorldUpdateResponse
                {
                    Timestamp = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()
                };

                foreach (var player in onlinePlayers)
                {
                    response.Players.Add(ConvertToPlayerInfo(player));
                }

                await responseStream.WriteAsync(response);
                await Task.Delay(100, context.CancellationToken); // 10 FPS
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error in world updates stream");
        }
        finally
        {
            _worldStreams.TryRemove(streamId, out _);
            _logger.LogInformation("Ended world updates stream for account {AccountId}", accountId);
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
