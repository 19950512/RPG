using System.ComponentModel.DataAnnotations;

namespace GameServer.Models;

public class Account
{
    [Key]
    public Guid Id { get; set; } = Guid.NewGuid();
    
    [Required]
    [EmailAddress]
    public string Email { get; set; } = string.Empty;
    
    [Required]
    public string PasswordHash { get; set; } = string.Empty;
    
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    
    public bool IsActive { get; set; } = true;
    
    // Navigation properties
    public virtual ICollection<Player> Players { get; set; } = new List<Player>();
    public virtual ICollection<AuthToken> AuthTokens { get; set; } = new List<AuthToken>();
    public virtual ICollection<ActiveToken> ActiveTokens { get; set; } = new List<ActiveToken>();
}
