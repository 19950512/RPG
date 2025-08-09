using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Hosting;

namespace GameServer.Services;

public class WorldEntityWarmupHostedService : IHostedService
{
    private readonly ILogger<WorldEntityWarmupHostedService> _logger;
    private readonly IWorldEntityManager _manager;

    public WorldEntityWarmupHostedService(ILogger<WorldEntityWarmupHostedService> logger, IWorldEntityManager manager)
    {
        _logger = logger;
        _manager = manager;
    }

    public async Task StartAsync(CancellationToken cancellationToken)
    {
        _logger.LogInformation("[Warmup] Iniciando warmup de entidades do mundo...");
        await _manager.ForceReloadAsync();
        var all = await _manager.GetAllEntitiesAsync();
        var list = all.ToList();
        _logger.LogInformation("[Warmup] Total de entidades após warmup: {Count}", list.Count);
    }

    public Task StopAsync(CancellationToken cancellationToken)
    {
        _logger.LogInformation("[Warmup] Finalizando.");
        return Task.CompletedTask;
    }
}
