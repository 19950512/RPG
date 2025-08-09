using Grpc.Core;
using Grpc.Core.Interceptors;
using System.Security.Claims;
using GameServer.Services;

namespace GameServer.Interceptors;

public class JwtAuthInterceptor : Interceptor
{
    private readonly IJwtTokenService _jwtTokenService;
    private readonly ILogger<JwtAuthInterceptor> _logger;
    private readonly HashSet<string> _publicMethods;

    public JwtAuthInterceptor(IJwtTokenService jwtTokenService, ILogger<JwtAuthInterceptor> logger)
    {
        _jwtTokenService = jwtTokenService;
        _logger = logger;
        
        // Methods that don't require authentication
        _publicMethods = new HashSet<string>
        {
            "/auth.AuthService/CreateAccount",
            "/auth.AuthService/Login",
            "/world.WorldService/GetWorldEntities",
            "/world.WorldService/InteractWithEntity",
            "/world.WorldService/GetWorldUpdates"
        };
    }

    public override async Task<TResponse> UnaryServerHandler<TRequest, TResponse>(
        TRequest request,
        ServerCallContext context,
        UnaryServerMethod<TRequest, TResponse> continuation)
    {
        var method = context.Method;
        
        _logger.LogInformation("🔍 Checking method: {Method}, IsPublic: {IsPublic}", method, _publicMethods.Contains(method));
        
        // Skip authentication for public methods
        if (_publicMethods.Contains(method))
        {
            _logger.LogInformation("🔓 Public method, skipping auth: {Method}", method);
            return await continuation(request, context);
        }

        // Extract JWT token from metadata
        var authHeader = context.RequestHeaders.FirstOrDefault(h => h.Key == "authorization");
        if (authHeader == null)
        {
            _logger.LogWarning("Missing authorization header for method: {Method}", method);
            throw new RpcException(new Status(StatusCode.Unauthenticated, "Missing authorization header"));
        }

        var token = authHeader.Value;
        if (string.IsNullOrEmpty(token) || !token.StartsWith("Bearer "))
        {
            _logger.LogWarning("Invalid authorization header format for method: {Method}", method);
            throw new RpcException(new Status(StatusCode.Unauthenticated, "Invalid authorization header format"));
        }

        // Remove "Bearer " prefix
        token = token.Substring(7);

        // Check if the token is in the active tokens list in the database
        if (!await _jwtTokenService.IsTokenActiveAsync(token))
        {
            _logger.LogWarning("Token is not active or has been revoked: {Token}", token);
            throw new RpcException(new Status(StatusCode.Unauthenticated, "Token has been revoked or is invalid."));
        }

        // Validate JWT token
        var principal = _jwtTokenService.ValidateToken(token);
        if (principal == null)
        {
            _logger.LogWarning("Invalid JWT token for method: {Method}", method);
            throw new RpcException(new Status(StatusCode.Unauthenticated, "Invalid or expired token"));
        }

        // Add user context to gRPC context
        var accountId = principal.FindFirst(ClaimTypes.NameIdentifier)?.Value;
        var email = principal.FindFirst(ClaimTypes.Email)?.Value;

        if (string.IsNullOrEmpty(accountId))
        {
            _logger.LogWarning("Missing account ID in JWT token for method: {Method}", method);
            throw new RpcException(new Status(StatusCode.Unauthenticated, "Invalid token claims"));
        }

        // Add custom headers with user info for the service to use
        context.RequestHeaders.Add("x-account-id", accountId);
        context.RequestHeaders.Add("x-account-email", email ?? "");

        _logger.LogInformation("Authenticated request for account {AccountId} on method {Method}", accountId, method);

        return await continuation(request, context);
    }

    public override async Task ServerStreamingServerHandler<TRequest, TResponse>(
        TRequest request,
        IServerStreamWriter<TResponse> responseStream,
        ServerCallContext context,
        ServerStreamingServerMethod<TRequest, TResponse> continuation)
    {
        var method = context.Method;
        
        _logger.LogInformation("🌊 Streaming authentication for method: {Method}", method);
        
        // Skip authentication for public methods
        if (_publicMethods.Contains(method))
        {
            _logger.LogInformation("🔓 Public method, skipping auth: {Method}", method);
            await continuation(request, responseStream, context);
            return;
        }

        // Extract JWT token from metadata
        var authHeader = context.RequestHeaders.FirstOrDefault(h => h.Key == "authorization");
        if (authHeader == null)
        {
            _logger.LogWarning("❌ Missing authorization header for streaming method: {Method}", method);
            throw new RpcException(new Status(StatusCode.Unauthenticated, "Missing authorization header"));
        }

        var token = authHeader.Value;
        _logger.LogInformation("🔑 Found auth header for streaming: {Method}, token length: {Length}", method, token?.Length ?? 0);
        
        if (string.IsNullOrEmpty(token) || !token.StartsWith("Bearer "))
        {
            _logger.LogWarning("❌ Invalid authorization header format for streaming method: {Method}", method);
            throw new RpcException(new Status(StatusCode.Unauthenticated, "Invalid authorization header format"));
        }

        // Remove "Bearer " prefix
        token = token.Substring(7);
        _logger.LogInformation("🔍 Processing token for streaming: {Method}, clean token length: {Length}", method, token.Length);

        // Check if the token is in the active tokens list in the database
        var isTokenActive = await _jwtTokenService.IsTokenActiveAsync(token);
        _logger.LogInformation("🗃️ Token active check for streaming: {Method}, active: {Active}", method, isTokenActive);
        
        if (!isTokenActive)
        {
            _logger.LogWarning("❌ Token is not active or has been revoked for streaming: {Method}", method);
            throw new RpcException(new Status(StatusCode.Unauthenticated, "Token has been revoked or is invalid."));
        }

        // Validate JWT token
        var principal = _jwtTokenService.ValidateToken(token);
        _logger.LogInformation("👤 Token validation for streaming: {Method}, valid: {Valid}", method, principal != null);
        
        if (principal == null)
        {
            _logger.LogWarning("❌ Invalid JWT token for streaming method: {Method}", method);
            throw new RpcException(new Status(StatusCode.Unauthenticated, "Invalid or expired token"));
        }

        // Add user context to gRPC context
        var accountId = principal.FindFirst(ClaimTypes.NameIdentifier)?.Value;
        var email = principal.FindFirst(ClaimTypes.Email)?.Value;

        _logger.LogInformation("🔐 Extracted claims for streaming: {Method}, accountId: {AccountId}, email: {Email}", method, accountId, email);

        if (string.IsNullOrEmpty(accountId))
        {
            _logger.LogWarning("❌ Missing account ID in JWT token for streaming method: {Method}", method);
            throw new RpcException(new Status(StatusCode.Unauthenticated, "Invalid token claims"));
        }

        // Add custom headers with user info for the service to use
        context.RequestHeaders.Add("x-account-id", accountId);
        context.RequestHeaders.Add("x-account-email", email ?? "");

        _logger.LogInformation("✅ Authenticated streaming request for account {AccountId} on method {Method}", accountId, method);

        await continuation(request, responseStream, context);
    }
}
