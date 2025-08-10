using System;
using System.Threading.Tasks;
using GameClient.Protos;
using Grpc.Net.Client;

namespace GameClient.Services;

public class PlayerClient
{
    private readonly PlayerService.PlayerServiceClient _client;

    public PlayerClient(GrpcChannel channel)
    {
        _client = new PlayerService.PlayerServiceClient(channel);
    }

    public async Task<PickUpItemResponse> PickUpItemAsync(string playerId, string itemId)
    {
        var request = new PickUpItemRequest
        {
            PlayerId = playerId,
            ItemId = itemId
        };

        return await _client.PickUpItemAsync(request);
    }

    public async Task<bool> TryPickUpItemAsync(string playerId, string itemId)
    {
        try
        {
            var response = await PickUpItemAsync(playerId, itemId);
            Console.WriteLine(response.Message);
            return response.Success;
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Erro ao tentar pegar o item: {ex.Message}");
            return false;
        }
    }
}
