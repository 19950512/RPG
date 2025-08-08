using Microsoft.EntityFrameworkCore;
using Serilog;
using GameServer.Data;
using GameServer.Services;
using GameServer.Interceptors;

var builder = WebApplication.CreateBuilder(args);

// Force Development environment for testing
builder.Environment.EnvironmentName = "Development";

// Configure Serilog
Log.Logger = new LoggerConfiguration()
    .ReadFrom.Configuration(builder.Configuration)
    .WriteTo.Console()
    .WriteTo.File("logs/gameserver-.log", rollingInterval: RollingInterval.Day)
    .CreateLogger();

builder.Host.UseSerilog();

builder.WebHost.ConfigureKestrel(options =>
{
    options.ListenAnyIP(5001, listenOptions =>
    {
        listenOptions.Protocols = Microsoft.AspNetCore.Server.Kestrel.Core.HttpProtocols.Http2;
    });
    options.ListenAnyIP(5002, listenOptions =>
    {
        listenOptions.Protocols = Microsoft.AspNetCore.Server.Kestrel.Core.HttpProtocols.Http1;
    });
});

// Add services to the container
builder.Services.AddDbContext<GameDbContext>(options =>
    options.UseNpgsql(builder.Configuration.GetConnectionString("DefaultConnection")));

// Register custom services
builder.Services.AddScoped<IJwtTokenService, JwtTokenService>();
builder.Services.AddSingleton<IWorldService, WorldService>();

// Add gRPC services
builder.Services.AddGrpc(options =>
{
    options.Interceptors.Add<JwtAuthInterceptor>();
    options.MaxReceiveMessageSize = 4 * 1024 * 1024; // 4MB
    options.MaxSendMessageSize = 4 * 1024 * 1024; // 4MB
});

// Add gRPC reflection for development
if (builder.Environment.IsDevelopment())
{
    builder.Services.AddGrpcReflection();
}

var app = builder.Build();

// Configure the HTTP request pipeline
if (app.Environment.IsDevelopment())
{
    app.MapGrpcReflectionService();
}

// Map gRPC services
app.MapGrpcService<GameServer.Services.AuthService>();
app.MapGrpcService<GameServer.Services.PlayerServiceImpl>();

// Health check endpoint
app.MapGet("/health", () => "Healthy");

Log.Information("GameServer starting...");

app.Run();

// Ensure to flush and stop internal timers/threads before application-exit
Log.CloseAndFlush();
