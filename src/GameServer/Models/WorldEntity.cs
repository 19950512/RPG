using System.ComponentModel.DataAnnotations;
using GameServer.Items;

namespace GameServer.Models;

public class WorldEntity
{
    [Key]
    public Guid Id { get; set; } = Guid.NewGuid();
    
    [Required]
    [MaxLength(100)]
    public string Name { get; set; } = string.Empty;
    
    [Required]
    [MaxLength(20)]
    public string EntityType { get; set; } = string.Empty; // "npc", "monster", "item"
    
    // Position
    public float PositionX { get; set; }
    public float PositionY { get; set; }
    
    // Health and Mana (for monsters)
    public int CurrentHp { get; set; }
    public int MaxHp { get; set; }
    public int CurrentMp { get; set; }
    public int MaxMp { get; set; }
    
    // Combat stats
    public int Attack { get; set; }
    public int Defense { get; set; }
    public float Speed { get; set; } = 1.0f;
    
    // State
    [MaxLength(20)]
    public string MovementState { get; set; } = "idle";
    public int FacingDirection { get; set; } = 1;
    public bool IsAlive { get; set; } = true;
    
    // Additional properties (stored as JSON)
    public string Properties { get; set; } = "{}";
    
    // Metadata
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public DateTime LastUpdate { get; set; } = DateTime.UtcNow;
    
    // For monsters - respawn information
    public DateTime? DeathTime { get; set; }
    public int RespawnDelaySeconds { get; set; } = 300; // 5 minutes default
    public float SpawnX { get; set; } // Original spawn position
    public float SpawnY { get; set; }

    // FK opcional para Item (se esta entidade representa um item físico do mundo)
    public Guid? ItemId { get; set; }
    public Item? Item { get; set; } // Associação com a classe abstrata Item
}
