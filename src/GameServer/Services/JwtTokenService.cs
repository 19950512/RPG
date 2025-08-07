using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Text;
using GameServer.Data;
using GameServer.Models;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;

namespace GameServer.Services;

public interface IJwtTokenService
{
    string GenerateToken(Account account);
    ClaimsPrincipal? ValidateToken(string token);
    Task<bool> IsTokenActiveAsync(string token);
    Task DeactivateTokenAsync(string token);
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
}
