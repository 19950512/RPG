using GameServer.Data;
using Microsoft.EntityFrameworkCore;

namespace GameServer.Services;

public class TokenCleanupHostedService : BackgroundService
{
    private readonly IServiceScopeFactory _scopeFactory;
    private readonly ILogger<TokenCleanupHostedService> _logger;
    private readonly TimeSpan _interval;

    public TokenCleanupHostedService(IServiceScopeFactory scopeFactory, ILogger<TokenCleanupHostedService> logger, IConfiguration config)
    {
        _scopeFactory = scopeFactory;
        _logger = logger;
        var minutes = config.GetValue<int>("Jwt:CleanupIntervalMinutes", 30);
        _interval = TimeSpan.FromMinutes(Math.Max(1, minutes));
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        _logger.LogInformation("TokenCleanupHostedService started (interval {Interval} minutes)", _interval.TotalMinutes);
        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                using var scope = _scopeFactory.CreateScope();
                var db = scope.ServiceProvider.GetRequiredService<GameDbContext>();
                var now = DateTime.UtcNow;

                // Remove ActiveTokens expirados
                var expiredActives = await db.ActiveTokens.Where(t => t.Expires < now).ToListAsync(stoppingToken);
                if (expiredActives.Count > 0)
                {
                    db.ActiveTokens.RemoveRange(expiredActives);
                }

                // Remove RefreshTokens expirados há mais de 7 dias (graça) ou revogados há mais de 7 dias
                var threshold = now.AddDays(-7);
                var oldRefresh = await db.RefreshTokens
                    .Where(r => (r.ExpiresAt < now && r.ExpiresAt < threshold) || (r.RevokedAt != null && r.RevokedAt < threshold))
                    .ToListAsync(stoppingToken);
                if (oldRefresh.Count > 0)
                {
                    db.RefreshTokens.RemoveRange(oldRefresh);
                }

                if (expiredActives.Count > 0 || oldRefresh.Count > 0)
                {
                    await db.SaveChangesAsync(stoppingToken);
                    _logger.LogInformation("Token cleanup removed {Active} active tokens and {Refresh} refresh tokens", expiredActives.Count, oldRefresh.Count);
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error running token cleanup");
            }

            try { await Task.Delay(_interval, stoppingToken); } catch { }
        }
        _logger.LogInformation("TokenCleanupHostedService stopping");
    }
}
