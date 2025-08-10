using System;
using GameServer.Models;

namespace GameServer.Items;

public class PotionMana : Item
{
    // Construtor padrão para EF Core
    public PotionMana()
    {
        Name = "Mana Potion";
        Description = "Restores a small amount of mana.";
        Sprite = "mana_potion_sprite";
    }

    // Construtor de conveniência
    public PotionMana(float positionX, float positionY) : this()
    {
        PositionX = positionX;
        PositionY = positionY;
    }

    public override bool CanUse() => true;
    public override bool CanEquip() => false;
    public override ItemType GetItemType() => ItemType.Consumable;
    public override string GetItemSubType() => "mana_potion";

    protected override bool OnUse(Guid playerId)
    {
        // Lógica para restaurar mana do jogador
        Console.WriteLine($"Player {playerId} usou uma poção de mana.");
        return true;
    }
}
