using System;
using System.Threading.Tasks;
using GameServer.Data;
using GameServer.Models;
using GameServer.Protos;
using Grpc.Core;

namespace GameServer.Services;

public class PlayerService : Protos.PlayerService.PlayerServiceBase
{
    private readonly ItemService _itemService;
    private readonly GameDbContext _context;

    public PlayerService(ItemService itemService, GameDbContext context)
    {
        _itemService = itemService;
        _context = context;
    }

    public override async Task<PickUpItemResponse> PickUpItem(PickUpItemRequest request, ServerCallContext context)
    {
        Guid playerId = Guid.Parse(request.PlayerId);
        Guid itemId = Guid.Parse(request.ItemId);

        bool success = await _itemService.PickUpItemAsync(playerId, itemId);

        return new PickUpItemResponse
        {
            Success = success,
            Message = success ? "Item picked up successfully." : "Failed to pick up item."
        };
    }
}
