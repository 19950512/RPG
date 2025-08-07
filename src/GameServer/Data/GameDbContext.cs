using Microsoft.EntityFrameworkCore;
using GameServer.Models;

namespace GameServer.Data;

public class GameDbContext : DbContext
{
    public GameDbContext(DbContextOptions<GameDbContext> options) : base(options) { }

    public DbSet<Account> Accounts { get; set; }
    public DbSet<Player> Players { get; set; }
    public DbSet<AuthToken> AuthTokens { get; set; }
    public DbSet<ActiveToken> ActiveTokens { get; set; }

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
            entity.Property(e => e.Token).HasMaxLength(255);
            
            entity.HasOne(e => e.Account)
                  .WithMany(a => a.ActiveTokens)
                  .HasForeignKey(e => e.AccountId)
                  .OnDelete(DeleteBehavior.Cascade);
        });
    }
}
