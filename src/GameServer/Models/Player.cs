using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace GameServer.Models;

public class Player
{
    [Key]
    public Guid Id { get; set; } = Guid.NewGuid();
    
    [Required]
    [ForeignKey(nameof(Account))]
    public Guid AccountId { get; set; }
    
    [Required]
    [MaxLength(50)]
    public string Name { get; set; } = string.Empty;
    
    [Required]
    [MaxLength(50)]
    public string Vocation { get; set; } = string.Empty;
    
    public int Experience { get; set; } = 0;
    
    public int Level { get; set; } = 1;
    
    // Navigation property
    public virtual Account Account { get; set; } = null!;
}
