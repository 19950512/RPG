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
