using System;

namespace GameServer.Items;

public class PotionHealth : Item
{
    // Construtor padrão exigido pelo EF Core (usa inicialização padrão)
    public PotionHealth()
    {
        Name = "Health Potion";
        Description = "Restores a small amount of health.";
        Sprite = "health_potion_sprite";
    }

    // Construtor de conveniência para criação manual no código
    public PotionHealth(float positionX, float positionY) : this()
    {
        PositionX = positionX;
        PositionY = positionY;
    }

    public override bool CanUse() => true;
    public override bool CanEquip() => false;
    public override ItemType GetItemType() => ItemType.Consumable;
    public override string GetItemSubType() => "health_potion";

    protected override bool OnUse(Guid playerId)
    {
        // Lógica para curar o jogador
        Console.WriteLine($"Player {playerId} usou uma poção de vida.");
        return true;
    }
}
