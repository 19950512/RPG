using System;

namespace GameServer.Items;

public class Sword : Item
{
    // Construtor padrão para EF Core
    public Sword()
    {
        Name = "Sword";
        Description = "A sturdy iron sword";
        Sprite = "sword_sprite";
    }

    // Construtor de conveniência
    public Sword(float positionX, float positionY) : this()
    {
        PositionX = positionX;
        PositionY = positionY;
    }

    public override bool CanUse() => false;
    public override bool CanEquip() => true;
    public override ItemType GetItemType() => ItemType.Equipment;
    public override string GetItemSubType() => "sword";

    protected override bool OnEquip(Guid playerId)
    {
        // Lógica para equipar a espada
        Console.WriteLine($"Player {playerId} equipou uma espada.");
        return true;
    }

    protected override bool OnUse(Guid playerId)
    {
        // Espadas não podem ser usadas diretamente
        return false;
    }
}
