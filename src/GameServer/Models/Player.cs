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
    
    // Position in the world
    public float PositionX { get; set; } = 960.0f; // Default spawn X (30 * 32)
    public float PositionY { get; set; } = 704.0f; // Default spawn Y (22 * 32)
    
    // Health and Mana
    public int CurrentHp { get; set; } = 100;
    public int MaxHp { get; set; } = 100;
    public int CurrentMp { get; set; } = 50;
    public int MaxMp { get; set; } = 50;
    
    // Combat stats
    public int Attack { get; set; } = 10;
    public int Defense { get; set; } = 5;
    public float Speed { get; set; } = 100.0f;
    
    // State
    public string MovementState { get; set; } = "idle"; // idle, walking, running, attacking, dead
    public int FacingDirection { get; set; } = 0; // 0=down, 1=left, 2=up, 3=right
    public bool IsOnline { get; set; } = false;
    public DateTime LastUpdate { get; set; } = DateTime.UtcNow;

    // Navigation property
    public virtual Account Account { get; set; } = null!;

    // Inventory
    public List<string> Inventory { get; set; } = new List<string>(); // IDs dos itens no inventário como string (GUID)
}
