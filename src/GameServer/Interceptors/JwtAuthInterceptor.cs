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
            "/auth.AuthService/Login"
            // Removed GetWorldEntities to enforce auth
            // Keeping other world methods protected by service-level header requirement
        };
    }

    public override async Task<TResponse> UnaryServerHandler<TRequest, TResponse>(
        TRequest request,
        ServerCallContext context,
        UnaryServerMethod<TRequest, TResponse> continuation)
    {
        var method = context.Method;

        if (_logger.IsEnabled(LogLevel.Debug))
            _logger.LogDebug("Auth check unary method={Method} public={Public}", method, _publicMethods.Contains(method));
        
        if (_publicMethods.Contains(method))
        {
            if (_logger.IsEnabled(LogLevel.Trace))
                _logger.LogTrace("Skipping auth (public) method={Method}", method);
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

        if (_logger.IsEnabled(LogLevel.Debug))
            _logger.LogDebug("Authenticated unary request account={AccountId} method={Method}", accountId, method);

        return await continuation(request, context);
    }

    public override async Task ServerStreamingServerHandler<TRequest, TResponse>(
        TRequest request,
        IServerStreamWriter<TResponse> responseStream,
        ServerCallContext context,
        ServerStreamingServerMethod<TRequest, TResponse> continuation)
    {
        var method = context.Method;
        if (_logger.IsEnabled(LogLevel.Debug))
            _logger.LogDebug("Auth check stream method={Method} public={Public}", method, _publicMethods.Contains(method));
        
        if (_publicMethods.Contains(method))
        {
            if (_logger.IsEnabled(LogLevel.Trace))
                _logger.LogTrace("Skipping auth (public) stream method={Method}", method);
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
        if (string.IsNullOrEmpty(token) || !token.StartsWith("Bearer "))
        {
            _logger.LogWarning("❌ Invalid authorization header format for streaming method: {Method}", method);
            throw new RpcException(new Status(StatusCode.Unauthenticated, "Invalid authorization header format"));
        }

        // Remove "Bearer " prefix
        token = token.Substring(7);

        // Check if the token is in the active tokens list in the database
        var isTokenActive = await _jwtTokenService.IsTokenActiveAsync(token);
        if (!isTokenActive)
        {
            _logger.LogWarning("❌ Token is not active or has been revoked for streaming: {Method}", method);
            throw new RpcException(new Status(StatusCode.Unauthenticated, "Token has been revoked or is invalid."));
        }

        // Validate JWT token
        var principal = _jwtTokenService.ValidateToken(token);
        if (principal == null)
        {
            _logger.LogWarning("❌ Invalid JWT token for streaming method: {Method}", method);
            throw new RpcException(new Status(StatusCode.Unauthenticated, "Invalid or expired token"));
        }

        // Add user context to gRPC context
        var accountId = principal.FindFirst(ClaimTypes.NameIdentifier)?.Value;
        var email = principal.FindFirst(ClaimTypes.Email)?.Value;

        if (string.IsNullOrEmpty(accountId))
        {
            _logger.LogWarning("❌ Missing account ID in JWT token for streaming method: {Method}", method);
            throw new RpcException(new Status(StatusCode.Unauthenticated, "Invalid token claims"));
        }

        // Add custom headers with user info for the service to use
        context.RequestHeaders.Add("x-account-id", accountId);
        context.RequestHeaders.Add("x-account-email", email ?? "");

        if (_logger.IsEnabled(LogLevel.Debug))
            _logger.LogDebug("Authenticated streaming request account={AccountId} method={Method}", accountId, method);

        await continuation(request, responseStream, context);
    }
}
