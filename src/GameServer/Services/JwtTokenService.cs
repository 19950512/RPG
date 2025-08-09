using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Text;
using GameServer.Data;
using GameServer.Models;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;
using System.Security.Cryptography;

namespace GameServer.Services;

public interface IJwtTokenService
{
    string GenerateToken(Account account);
    ClaimsPrincipal? ValidateToken(string token);
    Task<bool> IsTokenActiveAsync(string token);
    Task DeactivateTokenAsync(string token);
    Task<(string refreshToken, DateTime expires)> CreateRefreshTokenAsync(Account account, string? createdByIp = null);
    Task<RefreshToken?> GetValidRefreshTokenAsync(string refreshTokenPlain);
    Task InvalidateRefreshTokenAsync(string refreshTokenPlain, string? revokedByIp = null, string? replaceWithHash = null);
}

public class JwtTokenService : IJwtTokenService
{
    private readonly IConfiguration _configuration;
    private readonly GameDbContext _context;

    public JwtTokenService(IConfiguration configuration, GameDbContext context)
    {
        _configuration = configuration;
        _context = context;
    }

    public string GenerateToken(Account account)
    {
        var tokenHandler = new JwtSecurityTokenHandler();
        var key = Encoding.ASCII.GetBytes(_configuration["Jwt:SecretKey"] ?? throw new InvalidOperationException("JWT SecretKey not configured"));
        var tokenDescriptor = new SecurityTokenDescriptor
        {
            Subject = new ClaimsIdentity(new[]
            {
                new Claim(ClaimTypes.NameIdentifier, account.Id.ToString()),
                new Claim(ClaimTypes.Email, account.Email),
                new Claim(JwtRegisteredClaimNames.Sub, account.Id.ToString()),
                new Claim(JwtRegisteredClaimNames.Email, account.Email),
                new Claim(JwtRegisteredClaimNames.Jti, Guid.NewGuid().ToString()),
                new Claim(JwtRegisteredClaimNames.Iat, DateTimeOffset.UtcNow.ToUnixTimeSeconds().ToString(), ClaimValueTypes.Integer64)
            }),
            Expires = DateTime.UtcNow.AddMinutes(_configuration.GetValue<int>("Jwt:ExpirationMinutes")),
            SigningCredentials = new SigningCredentials(new SymmetricSecurityKey(key), SecurityAlgorithms.HmacSha256Signature)
        };
        var token = tokenHandler.CreateToken(tokenDescriptor);
        var tokenString = tokenHandler.WriteToken(token);

        _context.ActiveTokens.Add(new ActiveToken
        {
            Token = tokenString,
            AccountId = account.Id,
            Expires = token.ValidTo
        });
        _context.SaveChangesAsync().GetAwaiter().GetResult();

        return tokenString;
    }

    public ClaimsPrincipal? ValidateToken(string token)
    {
        var tokenHandler = new JwtSecurityTokenHandler();
        var key = Encoding.ASCII.GetBytes(_configuration["Jwt:SecretKey"] ?? throw new InvalidOperationException("JWT SecretKey not configured"));
        try
        {
            var principal = tokenHandler.ValidateToken(token, new TokenValidationParameters
            {
                ValidateIssuerSigningKey = true,
                IssuerSigningKey = new SymmetricSecurityKey(key),
                ValidateIssuer = false, // Disabled
                ValidateAudience = false, // Disabled
                ClockSkew = TimeSpan.Zero
            }, out SecurityToken validatedToken);

            return principal;
        }
        catch
        {
            return null;
        }
    }

    public async Task<bool> IsTokenActiveAsync(string token)
    {
        return await _context.ActiveTokens.AnyAsync(t => t.Token == token && t.Expires > DateTime.UtcNow);
    }

    public async Task DeactivateTokenAsync(string token)
    {
        var activeToken = await _context.ActiveTokens.FirstOrDefaultAsync(t => t.Token == token);
        if (activeToken != null)
        {
            _context.ActiveTokens.Remove(activeToken);
            await _context.SaveChangesAsync();
        }
    }

    private static string GenerateSecureToken(int size = 64)
    {
        var bytes = new byte[size];
        RandomNumberGenerator.Fill(bytes);
        return Convert.ToBase64String(bytes);
    }

    private static string HashToken(string token)
    {
        using var sha256 = SHA256.Create();
        var hash = sha256.ComputeHash(Encoding.UTF8.GetBytes(token));
        return Convert.ToBase64String(hash);
    }

    public async Task<(string refreshToken, DateTime expires)> CreateRefreshTokenAsync(Account account, string? createdByIp = null)
    {
        var plain = GenerateSecureToken();
        var hash = HashToken(plain);
        var expires = DateTime.UtcNow.AddDays(_configuration.GetValue<int>("Jwt:RefreshTokenDays", 7));
        var entity = new RefreshToken
        {
            AccountId = account.Id,
            TokenHash = hash,
            ExpiresAt = expires,
            CreatedAt = DateTime.UtcNow,
            CreatedByIp = createdByIp ?? string.Empty
        };
        _context.RefreshTokens.Add(entity);
        await _context.SaveChangesAsync();
        return (plain, expires);
    }

    public async Task<RefreshToken?> GetValidRefreshTokenAsync(string refreshTokenPlain)
    {
        var hash = HashToken(refreshTokenPlain);
        return await _context.RefreshTokens.FirstOrDefaultAsync(r => r.TokenHash == hash && r.RevokedAt == null && r.ExpiresAt > DateTime.UtcNow);
    }

    public async Task InvalidateRefreshTokenAsync(string refreshTokenPlain, string? revokedByIp = null, string? replaceWithHash = null)
    {
        var hash = HashToken(refreshTokenPlain);
        var token = await _context.RefreshTokens.FirstOrDefaultAsync(r => r.TokenHash == hash);
        if (token != null && token.RevokedAt == null)
        {
            token.RevokedAt = DateTime.UtcNow;
            token.RevokedByIp = revokedByIp;
            token.ReplacedByTokenHash = replaceWithHash;
            await _context.SaveChangesAsync();
        }
    }
}
