using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace GameServer.Models;

public class AuthToken
{
    [Key]
    public Guid Id { get; set; } = Guid.NewGuid();
    
    [Required]
    [ForeignKey(nameof(Account))]
    public Guid AccountId { get; set; }
    
    [Required]
    public string JwtToken { get; set; } = string.Empty;
    
    public DateTime ExpiresAt { get; set; }
    
    // Navigation property
    public virtual Account Account { get; set; } = null!;
}
