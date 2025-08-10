using System;
using System.ComponentModel.DataAnnotations.Schema;

namespace GameServer.Models;

public class ItemEvent
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public Guid ItemId { get; set; }
    public Guid PlayerId { get; set; }
    public ItemEventType EventType { get; set; }
    [Column("EventTime")] // mapeia para coluna existente no banco
    public DateTime Timestamp { get; set; }
    public string? Details { get; set; } // coluna opcional
}

public enum ItemEventType
{
    PickUp,
    Drop,
    Use
}
