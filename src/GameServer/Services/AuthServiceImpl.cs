using System.Text.RegularExpressions;
using Grpc.Core;
using Microsoft.EntityFrameworkCore;
using BCrypt.Net;
using GameServer.Data;
using GameServer.Models;
using GameServer.Protos;

namespace GameServer.Services
{
    public partial class AuthService : Protos.AuthService.AuthServiceBase
    {
        private readonly GameDbContext _dbContext;
        private readonly IJwtTokenService _jwtTokenService;
        private readonly ILogger<AuthService> _logger;

        public AuthService(GameDbContext dbContext, IJwtTokenService jwtTokenService, ILogger<AuthService> logger)
        {
            _dbContext = dbContext;
            _jwtTokenService = jwtTokenService;
            _logger = logger;
        }

        public override async Task<CreateAccountResponse> CreateAccount(CreateAccountRequest request, ServerCallContext context)
        {
            try
            {
                // Validate input
                if (string.IsNullOrWhiteSpace(request.Email) || string.IsNullOrWhiteSpace(request.Password))
                {
                    return new CreateAccountResponse
                    {
                        Success = false,
                        Message = "Email and password are required"
                    };
                }

                if (!IsValidEmail(request.Email))
                {
                    return new CreateAccountResponse
                    {
                        Success = false,
                        Message = "Invalid email format"
                    };
                }

                if (request.Password.Length < 6)
                {
                    return new CreateAccountResponse
                    {
                        Success = false,
                        Message = "Password must be at least 6 characters long"
                    };
                }

                // Check if email already exists
                var existingAccount = await _dbContext.Accounts
                    .FirstOrDefaultAsync(a => a.Email.ToLower() == request.Email.ToLower());

                if (existingAccount != null)
                {
                    return new CreateAccountResponse
                    {
                        Success = false,
                        Message = "Email already in use"
                    };
                }

                // Create new account
                var passwordHash = BCrypt.Net.BCrypt.HashPassword(request.Password, BCrypt.Net.BCrypt.GenerateSalt());
                
                var account = new Account
                {
                    Email = request.Email.ToLower(),
                    PasswordHash = passwordHash,
                    CreatedAt = DateTime.UtcNow,
                    IsActive = true
                };

                _dbContext.Accounts.Add(account);
                await _dbContext.SaveChangesAsync();

                _logger.LogInformation("Account created successfully for email: {Email}", request.Email);

                return new CreateAccountResponse
                {
                    Success = true,
                    Message = "Account created successfully",
                    AccountId = account.Id.ToString()
                };
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error creating account for email: {Email}", request.Email);
                return new CreateAccountResponse
                {
                    Success = false,
                    Message = "Internal server error"
                };
            }
        }

        public override async Task<LoginResponse> Login(LoginRequest request, ServerCallContext context)
        {
            try
            {
                // Validate input
                if (string.IsNullOrWhiteSpace(request.Email) || string.IsNullOrWhiteSpace(request.Password))
                {
                    return new LoginResponse
                    {
                        Success = false,
                        Message = "Email and password are required"
                    };
                }

                // Find account
                var account = await _dbContext.Accounts
                    .FirstOrDefaultAsync(a => a.Email.ToLower() == request.Email.ToLower() && a.IsActive);

                if (account == null)
                {
                    _logger.LogWarning("Login attempt with non-existent email: {Email}", request.Email);
                    return new LoginResponse
                    {
                        Success = false,
                        Message = "Invalid email or password"
                    };
                }

                // Verify password
                if (!BCrypt.Net.BCrypt.Verify(request.Password, account.PasswordHash))
                {
                    _logger.LogWarning("Login attempt with invalid password for email: {Email}", request.Email);
                    return new LoginResponse
                    {
                        Success = false,
                        Message = "Invalid email or password"
                    };
                }

                // Generate JWT token (which is now also stored in the DB by the service)
                var jwtToken = _jwtTokenService.GenerateToken(account);
                var token = await _dbContext.ActiveTokens.FirstAsync(t => t.Token == jwtToken);

                // Create refresh token
                var (refreshToken, refreshExpires) = await _jwtTokenService.CreateRefreshTokenAsync(account, context.Peer);

                _logger.LogInformation("Login successful for email: {Email}", request.Email);

                return new LoginResponse
                {
                    Success = true,
                    Message = "Login successful",
                    JwtToken = jwtToken,
                    ExpiresAt = ((DateTimeOffset)token.Expires).ToUnixTimeSeconds(),
                    RefreshToken = refreshToken,
                    RefreshExpiresAt = ((DateTimeOffset)refreshExpires).ToUnixTimeSeconds()
                };
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error during login for email: {Email}", request.Email);
                return new LoginResponse
                {
                    Success = false,
                    Message = "Internal server error"
                };
            }
        }

        public override async Task<RefreshTokenResponse> RefreshToken(RefreshTokenRequest request, ServerCallContext context)
        {
            try
            {
                if (string.IsNullOrWhiteSpace(request.RefreshToken))
                {
                    return new RefreshTokenResponse { Success = false, Message = "Refresh token required" };
                }

                var existing = await _jwtTokenService.GetValidRefreshTokenAsync(request.RefreshToken);
                if (existing == null)
                {
                    return new RefreshTokenResponse { Success = false, Message = "Invalid or expired refresh token" };
                }

                var account = await _dbContext.Accounts.FirstAsync(a => a.Id == existing.AccountId);

                // Gera novo JWT
                var newJwt = _jwtTokenService.GenerateToken(account);
                var active = await _dbContext.ActiveTokens.FirstAsync(t => t.Token == newJwt);

                // Rotaciona refresh token
                var (newRefreshPlain, newRefreshExpires) = await _jwtTokenService.CreateRefreshTokenAsync(account, context.Peer);

                // Invalida o antigo (link para novo hash)
                await _jwtTokenService.InvalidateRefreshTokenAsync(request.RefreshToken, context.Peer);

                return new RefreshTokenResponse
                {
                    Success = true,
                    Message = "Token refreshed",
                    JwtToken = newJwt,
                    ExpiresAt = ((DateTimeOffset)active.Expires).ToUnixTimeSeconds(),
                    RefreshToken = newRefreshPlain,
                    RefreshExpiresAt = ((DateTimeOffset)newRefreshExpires).ToUnixTimeSeconds()
                };
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error refreshing token");
                return new RefreshTokenResponse { Success = false, Message = "Internal server error" };
            }
        }

        public override async Task<LogoutResponse> Logout(LogoutRequest request, ServerCallContext context)
        {
            try
            {
                // Revogar JWT (se fornecido) - caso não esteja no header
                if (!string.IsNullOrWhiteSpace(request.JwtToken))
                {
                    await _jwtTokenService.DeactivateTokenAsync(request.JwtToken);
                }
                else
                {
                    var authHeader = context.RequestHeaders.FirstOrDefault(h => h.Key == "authorization")?.Value;
                    if (!string.IsNullOrEmpty(authHeader) && authHeader.StartsWith("Bearer "))
                    {
                        var raw = authHeader.Substring(7);
                        await _jwtTokenService.DeactivateTokenAsync(raw);
                    }
                }

                // Revogar refresh token se enviado
                if (!string.IsNullOrWhiteSpace(request.RefreshToken))
                {
                    await _jwtTokenService.InvalidateRefreshTokenAsync(request.RefreshToken, context.Peer);
                }

                return new LogoutResponse { Success = true, Message = "Logged out" };
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error on logout");
                return new LogoutResponse { Success = false, Message = "Internal server error" };
            }
        }

        [GeneratedRegex(@"^[^@\s]+@[^@\s]+\.[^@\s]+$", RegexOptions.IgnoreCase, "pt-BR")]
        private static partial Regex EmailRegex();
        private static bool IsValidEmail(string email)
        {
            return !string.IsNullOrWhiteSpace(email) && EmailRegex().IsMatch(email);
        }
    }
}
