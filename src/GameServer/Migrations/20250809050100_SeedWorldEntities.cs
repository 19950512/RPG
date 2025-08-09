using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace GameServer.Migrations
{
    public partial class SeedWorldEntities : Migration
    {
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql(@"
INSERT INTO ""WorldEntities"" (
    ""Id"", ""Name"", ""EntityType"", ""PositionX"", ""PositionY"", ""CurrentHp"", ""MaxHp"", ""CurrentMp"", ""MaxMp"", ""Attack"", ""Defense"", ""Speed"", ""MovementState"", ""FacingDirection"", ""IsAlive"", ""Properties"", ""CreatedAt"", ""LastUpdate"", ""DeathTime"", ""RespawnDelaySeconds"", ""SpawnX"", ""SpawnY""
) VALUES
(gen_random_uuid(),'Village Elder','npc',500,500,100,100,0,0,0,10,1.0,'idle',0,true,'{""dialog"": ""Welcome to our village, traveler! Beware of the monsters to the north.""}',NOW(),NOW(),NULL,0,500,500),
(gen_random_uuid(),'Merchant','npc',600,500,80,80,0,0,0,5,1.0,'idle',0,true,'{""dialog"": ""I sell the finest weapons and armor! Come back when you have gold.""}',NOW(),NOW(),NULL,0,600,500),
(gen_random_uuid(),'Orc Warrior 1','monster',400,300,50,50,0,0,12,3,1.0,'idle',0,true,'{""type"": ""orc"", ""aggressive"": ""true""}',NOW(),NOW(),NULL,300,400,300),
(gen_random_uuid(),'Orc Warrior 2','monster',500,300,50,50,0,0,12,3,1.0,'idle',0,true,'{""type"": ""orc"", ""aggressive"": ""true""}',NOW(),NOW(),NULL,300,500,300),
(gen_random_uuid(),'Orc Warrior 3','monster',600,300,50,50,0,0,12,3,1.0,'idle',0,true,'{""type"": ""orc"", ""aggressive"": ""true""}',NOW(),NOW(),NULL,300,600,300),
(gen_random_uuid(),'Orc Warrior 4','monster',700,300,50,50,0,0,12,3,1.0,'idle',0,true,'{""type"": ""orc"", ""aggressive"": ""true""}',NOW(),NOW(),NULL,300,700,300),
(gen_random_uuid(),'Orc Warrior 5','monster',800,300,50,50,0,0,12,3,1.0,'idle',0,true,'{""type"": ""orc"", ""aggressive"": ""true""}',NOW(),NOW(),NULL,300,800,300),
(gen_random_uuid(),'Troll 1','monster',300,200,100,100,20,20,20,8,0.8,'idle',0,true,'{""type"": ""troll"", ""aggressive"": ""true""}',NOW(),NOW(),NULL,600,300,200),
(gen_random_uuid(),'Troll 2','monster',450,200,100,100,20,20,20,8,0.8,'idle',0,true,'{""type"": ""troll"", ""aggressive"": ""true""}',NOW(),NOW(),NULL,600,450,200),
(gen_random_uuid(),'Troll 3','monster',600,200,100,100,20,20,20,8,0.8,'idle',0,true,'{""type"": ""troll"", ""aggressive"": ""true""}',NOW(),NOW(),NULL,600,600,200),
(gen_random_uuid(),'Health Potion','item',550,450,1,1,0,0,0,0,0.0,'idle',0,true,'{""type"": ""consumable"", ""effect"": ""heal"", ""value"": ""25""}',NOW(),NOW(),NULL,0,550,450),
(gen_random_uuid(),'Mana Potion','item',570,450,1,1,0,0,0,0,0.0,'idle',0,true,'{""type"": ""consumable"", ""effect"": ""mana"", ""value"": ""15""}',NOW(),NOW(),NULL,0,570,450),
(gen_random_uuid(),'Sword','item',650,480,1,1,0,0,0,0,0.0,'idle',0,true,'{""type"": ""weapon"", ""attack_bonus"": ""5"", ""description"": ""A sturdy iron sword""}',NOW(),NOW(),NULL,0,650,480);
");
        }

        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql("DELETE FROM \"WorldEntities\" WHERE \"Name\" IN ('Village Elder','Merchant','Orc Warrior 1','Orc Warrior 2','Orc Warrior 3','Orc Warrior 4','Orc Warrior 5','Troll 1','Troll 2','Troll 3','Health Potion','Mana Potion','Sword');");
        }
    }
}
