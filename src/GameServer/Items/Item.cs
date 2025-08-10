using System;
using System.ComponentModel.DataAnnotations;

namespace GameServer.Items;

public abstract class Item
{
    public Guid Id { get; set; } = Guid.NewGuid();

    [Required]
    [StringLength(100)]
    public string Name { get; set; } = string.Empty;

    [StringLength(500)]
    public string Description { get; set; } = string.Empty;

    [StringLength(100)]
    public string Sprite { get; set; } = string.Empty;

    public int Quantity { get; set; } = 1;

    public float? PositionX { get; set; } // Permite valores nulos para indicar que o item não está no mapa
    public float? PositionY { get; set; } // Permite valores nulos para indicar que o item não está no mapa

    public Guid? OwnerId { get; set; } // Propriedade para rastrear o dono do item

    public abstract bool CanUse();
    public abstract bool CanEquip();
    public abstract ItemType GetItemType();
    public abstract string GetItemSubType();

    protected abstract bool OnUse(Guid playerId);
    protected virtual bool OnEquip(Guid playerId) => false;
    protected virtual bool OnUnequip(Guid playerId) => false;

    public virtual string GetDescription()
    {
        return $"{Name}: {Description}";
    }

    public Models.WorldEntity ToWorldEntity()
    {
        return new Models.WorldEntity
        {
            Name = this.Name,
            EntityType = "item",
            PositionX = this.PositionX ?? 0.0f, // Define um valor padrão caso seja nulo
            PositionY = this.PositionY ?? 0.0f, // Define um valor padrão caso seja nulo
            Properties = System.Text.Json.JsonSerializer.Serialize(new
            {
                type = GetItemType().ToString().ToLower(),
                subtype = GetItemSubType(),
                description = Description,
                sprite = Sprite,
                quantity = Quantity
            })
        };
    }
}

public enum ItemType
{
    Consumable,
    Equipment,
    Quest,
    Misc
}
