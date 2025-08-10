using Microsoft.EntityFrameworkCore;
using GameServer.Models;
using GameServer.Items; // Adiciona o namespace correto para a classe Item

namespace GameServer.Data;

public class GameDbContext : DbContext
{
    public GameDbContext(DbContextOptions<GameDbContext> options) : base(options) { }

    public DbSet<Account> Accounts { get; set; }
    public DbSet<Player> Players { get; set; }
    public DbSet<AuthToken> AuthTokens { get; set; }
    public DbSet<ActiveToken> ActiveTokens { get; set; }
    public DbSet<WorldEntity> WorldEntities { get; set; }
    public DbSet<GameServer.Models.RefreshToken> RefreshTokens { get; set; } = null!;
    public DbSet<Item> Items { get; set; } // Adiciona suporte para a entidade Item
    public DbSet<ItemEvent> ItemEvents { get; set; } // Adiciona suporte para eventos de itens

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);

        // Account configuration
        modelBuilder.Entity<Account>(entity =>
        {
            entity.HasKey(e => e.Id);
            entity.HasIndex(e => e.Email).IsUnique();
            entity.Property(e => e.Email).HasMaxLength(255);
            entity.Property(e => e.PasswordHash).HasMaxLength(255);
        });

        // Player configuration
        modelBuilder.Entity<Player>(entity =>
        {
            entity.HasKey(e => e.Id);
            entity.HasIndex(e => e.Name).IsUnique();
            entity.Property(e => e.Name).HasMaxLength(50);
            entity.Property(e => e.Vocation).HasMaxLength(50);
            entity.Property(e => e.MovementState).HasMaxLength(20);
            
            // Set default values
            entity.Property(e => e.PositionX).HasDefaultValue(960.0f);
            entity.Property(e => e.PositionY).HasDefaultValue(704.0f);
            entity.Property(e => e.CurrentHp).HasDefaultValue(100);
            entity.Property(e => e.MaxHp).HasDefaultValue(100);
            entity.Property(e => e.CurrentMp).HasDefaultValue(50);
            entity.Property(e => e.MaxMp).HasDefaultValue(50);
            entity.Property(e => e.Attack).HasDefaultValue(10);
            entity.Property(e => e.Defense).HasDefaultValue(5);
            entity.Property(e => e.Speed).HasDefaultValue(100.0f);
            entity.Property(e => e.MovementState).HasDefaultValue("idle");
            entity.Property(e => e.FacingDirection).HasDefaultValue(0);
            entity.Property(e => e.IsOnline).HasDefaultValue(false);
            
            entity.HasOne(e => e.Account)
                  .WithMany(a => a.Players)
                  .HasForeignKey(e => e.AccountId)
                  .OnDelete(DeleteBehavior.Cascade);
        });

        // AuthToken configuration
        modelBuilder.Entity<AuthToken>(entity =>
        {
            entity.HasKey(e => e.Id);
            entity.Property(e => e.JwtToken).HasMaxLength(1000);
            
            entity.HasOne(e => e.Account)
                  .WithMany(a => a.AuthTokens)
                  .HasForeignKey(e => e.AccountId)
                  .OnDelete(DeleteBehavior.Cascade);
        });

        // ActiveToken configuration
        modelBuilder.Entity<ActiveToken>(entity =>
        {
            entity.HasKey(e => e.Id);
            entity.Property(e => e.Token).HasColumnType("text"); // Remove limit for JWT tokens
            
            entity.HasOne(e => e.Account)
                  .WithMany(a => a.ActiveTokens)
                  .HasForeignKey(e => e.AccountId)
                  .OnDelete(DeleteBehavior.Cascade);
        });

        // WorldEntity configuration
        modelBuilder.Entity<WorldEntity>(entity =>
        {
            entity.HasKey(e => e.Id);
            entity.HasIndex(e => e.EntityType);
            entity.Property(e => e.Name).HasMaxLength(100);
            entity.Property(e => e.EntityType).HasMaxLength(20);
            entity.Property(e => e.MovementState).HasMaxLength(20);
            entity.Property(e => e.Properties).HasDefaultValue("{}");
            entity.HasOne(e => e.Item)
                  .WithMany() // sem navegação reversa em Item
                  .HasForeignKey(e => e.ItemId)
                  .IsRequired(false)
                  .OnDelete(DeleteBehavior.SetNull);
        });

        // Configuração da entidade Item (TPH com discriminador)
        var itemBuilder = modelBuilder.Entity<Item>();
        itemBuilder.HasKey(e => e.Id);
        itemBuilder.Property(e => e.Name).HasMaxLength(100);
        itemBuilder.Property(e => e.Description).HasMaxLength(255);
        itemBuilder.Property(e => e.PositionX);
        itemBuilder.Property(e => e.PositionY);
        itemBuilder.Property(e => e.OwnerId).IsRequired(false);
        itemBuilder.HasDiscriminator<string>("item_type")
                   .HasValue<Sword>("sword")
                   .HasValue<PotionHealth>("health_potion")
                   .HasValue<PotionMana>("mana_potion");

        // Registrar concretos
        modelBuilder.Entity<Sword>();
        modelBuilder.Entity<PotionHealth>();
        modelBuilder.Entity<PotionMana>();

        // Configuração da entidade ItemEvent
        modelBuilder.Entity<ItemEvent>(entity =>
        {
            entity.HasKey(e => e.Id);
            entity.Property(e => e.EventType).HasMaxLength(50);
            entity.Property(e => e.Timestamp).IsRequired();
        });
    }
}
