using Grpc.Core;
using Microsoft.EntityFrameworkCore;
using GameServer.Data;
using GameServer.Models;
using GameServer.Protos;

namespace GameServer.Services;

public class PlayerService : GameServer.Protos.PlayerService.PlayerServiceBase
{
    private readonly GameDbContext _dbContext;
    private readonly ILogger<PlayerService> _logger;

    public PlayerService(GameDbContext dbContext, ILogger<PlayerService> logger)
    {
        _dbContext = dbContext;
        _logger = logger;
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
                    Level = p.Level
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
}
