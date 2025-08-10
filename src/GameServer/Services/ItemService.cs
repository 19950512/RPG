using System;
using System.Linq;
using System.Threading.Tasks;
using GameServer.Data;
using GameServer.Models;
using GameServer.Items; // Importa o namespace correto para a classe Item
using Microsoft.EntityFrameworkCore;

namespace GameServer.Services;

public class ItemService
{
    private readonly GameDbContext _context;

    public ItemService(GameDbContext context)
    {
        _context = context;
    }

    public async Task<bool> PickUpItemAsync(Guid playerId, Guid itemId)
    {
        Player? player = await _context.Players.FindAsync(playerId); // Tipagem explícita para player
        Item? item = await _context.Items.FindAsync(itemId); // Tipagem explícita para item

        if (player == null || item == null || item.OwnerId != null)
        {
            return false; // Jogador ou item não encontrado, ou item já possui dono
        }

        // Adiciona item ao inventário do jogador
        if (player.Inventory == null)
        {
            player.Inventory = new List<string>();
        }
        player.Inventory.Add(item.Id.ToString());
        item.OwnerId = player.Id;

        // Remover o item do mapa
        item.PositionX = null;
        item.PositionY = null;

        // Registrar evento de rastreamento do item
        ItemEvent itemEvent = new ItemEvent
        {
            ItemId = item.Id,
            PlayerId = player.Id,
            EventType = ItemEventType.PickUp,
            Timestamp = DateTime.UtcNow
        };
        _context.ItemEvents.Add(itemEvent);

        await _context.SaveChangesAsync();
        return true;
    }

    // Novo método com detalhamento de falha
    public async Task<(bool Success, string Reason)> TryPickUpItemAsync(Guid playerId, Guid itemId)
    {
        Player? player = await _context.Players.FindAsync(playerId);
        if (player == null)
        {
            return (false, "Jogador não encontrado");
        }
        Item? item = await _context.Items.FindAsync(itemId);
        if (item == null)
        {
            return (false, "Item não encontrado");
        }
        if (item.OwnerId != null)
        {
            return (false, "Item já possui dono");
        }

        if (player.Inventory == null)
        {
            player.Inventory = new List<string>();
        }
        player.Inventory.Add(item.Id.ToString());
        item.OwnerId = player.Id;
        item.PositionX = null;
        item.PositionY = null;

        ItemEvent itemEvent = new ItemEvent
        {
            ItemId = item.Id,
            PlayerId = player.Id,
            EventType = ItemEventType.PickUp,
            Timestamp = DateTime.UtcNow
        };
        _context.ItemEvents.Add(itemEvent);

        await _context.SaveChangesAsync();
        return (true, "Item coletado com sucesso.");
    }

    public async Task<Guid?> ResolveWorldEntityItemAsync(Guid worldEntityId)
    {
        var entity = await _context.WorldEntities.FirstOrDefaultAsync(w => w.Id == worldEntityId);
        return entity?.ItemId;
    }
}
