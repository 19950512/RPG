-- Initialize database with optimizations for game server
-- This script runs when the PostgreSQL container starts for the first time

-- Create extensions for better performance
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create the main tables for the game server

-- Accounts table
CREATE TABLE IF NOT EXISTS "Accounts" (
    "Id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "Email" VARCHAR(255) NOT NULL UNIQUE,
    "PasswordHash" VARCHAR(255) NOT NULL,
    "CreatedAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "IsActive" BOOLEAN NOT NULL DEFAULT TRUE
);

-- Players table
CREATE TABLE IF NOT EXISTS "Players" (
    "Id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "AccountId" UUID NOT NULL REFERENCES "Accounts"("Id") ON DELETE CASCADE,
    "Name" VARCHAR(50) NOT NULL UNIQUE,
    "Vocation" VARCHAR(50) NOT NULL,
    "Experience" INTEGER NOT NULL DEFAULT 0,
    "Level" INTEGER NOT NULL DEFAULT 1,
    
    -- Position
    "PositionX" REAL NOT NULL DEFAULT 960,
    "PositionY" REAL NOT NULL DEFAULT 704,
    
    -- Health and Mana
    "CurrentHp" INTEGER NOT NULL DEFAULT 100,
    "MaxHp" INTEGER NOT NULL DEFAULT 100,
    "CurrentMp" INTEGER NOT NULL DEFAULT 50,
    "MaxMp" INTEGER NOT NULL DEFAULT 50,
    
    -- Combat stats
    "Attack" INTEGER NOT NULL DEFAULT 10,
    "Defense" INTEGER NOT NULL DEFAULT 5,
    "Speed" REAL NOT NULL DEFAULT 100,
    
    -- State
    "MovementState" VARCHAR(20) NOT NULL DEFAULT 'idle',
    "FacingDirection" INTEGER NOT NULL DEFAULT 0,
    "IsOnline" BOOLEAN NOT NULL DEFAULT false,
    "LastUpdate" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Inventory
    "Inventory" TEXT[] DEFAULT '{}'
);

-- AuthTokens table
CREATE TABLE IF NOT EXISTS "AuthTokens" (
    "Id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "AccountId" UUID NOT NULL REFERENCES "Accounts"("Id") ON DELETE CASCADE,
    "JwtToken" VARCHAR(1000) NOT NULL,
    "ExpiresAt" TIMESTAMP WITH TIME ZONE NOT NULL
);

-- ActiveTokens table
CREATE TABLE IF NOT EXISTS "ActiveTokens" (
    "Id" SERIAL PRIMARY KEY,
    "AccountId" UUID NOT NULL REFERENCES "Accounts"("Id") ON DELETE CASCADE,
    "Token" TEXT NOT NULL,
    "Expires" TIMESTAMP WITH TIME ZONE NOT NULL
);

-- RefreshTokens table
CREATE TABLE IF NOT EXISTS "RefreshTokens" (
    "Id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "AccountId" UUID NOT NULL REFERENCES "Accounts"("Id") ON DELETE CASCADE,
    "TokenHash" VARCHAR(512) NOT NULL,
    "ExpiresAt" TIMESTAMP WITH TIME ZONE NOT NULL,
    "CreatedAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "CreatedByIp" VARCHAR(45) NOT NULL DEFAULT '',
    "RevokedAt" TIMESTAMP WITH TIME ZONE NULL,
    "RevokedByIp" VARCHAR(45) NULL,
    "ReplacedByTokenHash" VARCHAR(512) NULL
);

-- WorldEntities table for NPCs, monsters, and items
CREATE TABLE IF NOT EXISTS "WorldEntities" (
    "Id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "Name" VARCHAR(100) NOT NULL,
    "EntityType" VARCHAR(20) NOT NULL, -- "npc", "monster", "item"
    
    -- Position
    "PositionX" REAL NOT NULL,
    "PositionY" REAL NOT NULL,
    "SpawnX" REAL NOT NULL,
    "SpawnY" REAL NOT NULL,
    
    -- Health and Mana
    "CurrentHp" INTEGER NOT NULL DEFAULT 100,
    "MaxHp" INTEGER NOT NULL DEFAULT 100,
    "CurrentMp" INTEGER NOT NULL DEFAULT 0,
    "MaxMp" INTEGER NOT NULL DEFAULT 0,
    
    -- Combat stats
    "Attack" INTEGER NOT NULL DEFAULT 0,
    "Defense" INTEGER NOT NULL DEFAULT 0,
    "Speed" REAL NOT NULL DEFAULT 1.0,
    
    -- State
    "MovementState" VARCHAR(20) NOT NULL DEFAULT 'idle',
    "FacingDirection" INTEGER NOT NULL DEFAULT 0,
    "IsAlive" BOOLEAN NOT NULL DEFAULT true,
    "DeathTime" TIMESTAMP WITH TIME ZONE NULL,
    "RespawnDelaySeconds" INTEGER NOT NULL DEFAULT 0,
    "LastUpdate" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "CreatedAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Additional properties as JSON
    "Properties" TEXT NOT NULL DEFAULT '{}'
);

-- Items table (TPH discriminator + metadata)
DROP TABLE IF EXISTS "Items" CASCADE;
CREATE TABLE "Items" (
    "Id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "Name" VARCHAR(100) NOT NULL,
    "item_type" VARCHAR(50) NOT NULL,              -- Discriminador EF (sword, health_potion, mana_potion)
    "Description" VARCHAR(500) NULL,
    "Sprite" VARCHAR(100) NULL,
    "Quantity" INT NOT NULL DEFAULT 1,
    "OwnerId" UUID NULL REFERENCES "Players"("Id") ON DELETE SET NULL,
    "PositionX" REAL NULL,
    "PositionY" REAL NULL,
    "CreatedAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "LastUpdate" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Relacionamento opcional WorldEntities -> Items (ItemId)
ALTER TABLE "WorldEntities"
    ADD COLUMN IF NOT EXISTS "ItemId" UUID NULL;

-- Garantir recriação segura da FK (PostgreSQL não suporta IF NOT EXISTS em ADD CONSTRAINT)
ALTER TABLE "WorldEntities" DROP CONSTRAINT IF EXISTS "FK_WorldEntities_Items_ItemId";
ALTER TABLE "WorldEntities"
    ADD CONSTRAINT "FK_WorldEntities_Items_ItemId" FOREIGN KEY ("ItemId") REFERENCES "Items"("Id") ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS "IX_WorldEntities_ItemId" ON "WorldEntities" ("ItemId");

-- ItemEvents table to track events related to items
DROP TABLE IF EXISTS "ItemEvents" CASCADE;
CREATE TABLE "ItemEvents" (
    "Id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "ItemId" UUID NOT NULL REFERENCES "Items"("Id") ON DELETE CASCADE,
    "EventType" VARCHAR(50) NOT NULL, -- Ex: PickUp, Drop, Use
    "PlayerId" UUID NULL REFERENCES "Players"("Id") ON DELETE SET NULL,
    "EventTime" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "Details" TEXT NULL -- JSON adicional
);

-- Indexes específicos para Items
CREATE INDEX IF NOT EXISTS "IX_Items_ItemType" ON "Items" ("item_type");
CREATE INDEX IF NOT EXISTS "IX_Items_OwnerId" ON "Items" ("OwnerId");
CREATE INDEX IF NOT EXISTS "IX_ItemEvents_ItemId" ON "ItemEvents" ("ItemId");
CREATE INDEX IF NOT EXISTS "IX_ItemEvents_PlayerId" ON "ItemEvents" ("PlayerId");

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS "IX_Accounts_Email" ON "Accounts" ("Email");
CREATE INDEX IF NOT EXISTS "IX_Players_AccountId" ON "Players" ("AccountId");
CREATE INDEX IF NOT EXISTS "IX_Players_Name" ON "Players" ("Name");
CREATE INDEX IF NOT EXISTS "IX_AuthTokens_AccountId" ON "AuthTokens" ("AccountId");
CREATE INDEX IF NOT EXISTS "IX_ActiveTokens_AccountId" ON "ActiveTokens" ("AccountId");
CREATE INDEX IF NOT EXISTS "IX_ActiveTokens_Expires" ON "ActiveTokens" ("Expires");
CREATE INDEX IF NOT EXISTS "IX_RefreshTokens_AccountId" ON "RefreshTokens" ("AccountId");
CREATE INDEX IF NOT EXISTS "IX_RefreshTokens_TokenHash" ON "RefreshTokens" ("TokenHash");
CREATE INDEX IF NOT EXISTS "IX_WorldEntities_EntityType" ON "WorldEntities" ("EntityType");
CREATE INDEX IF NOT EXISTS "IX_WorldEntities_IsAlive" ON "WorldEntities" ("IsAlive");

-- Create a function to automatically update timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE gameserver TO gameuser;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO gameuser;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO gameuser;

-- Insert initial world entities (NPCs, monsters, items)
INSERT INTO "WorldEntities" ("Name", "EntityType", "PositionX", "PositionY", "SpawnX", "SpawnY", "CurrentHp", "MaxHp", "CurrentMp", "MaxMp", "Attack", "Defense", "Speed", "RespawnDelaySeconds", "Properties") VALUES
-- NPCs
('Village Elder', 'npc', 500, 500, 500, 500, 100, 100, 0, 0, 0, 10, 1.0, 0, '{"dialog": "Welcome to our village, traveler! Beware of the monsters to the north."}'),
('Merchant', 'npc', 600, 500, 600, 500, 80, 80, 0, 0, 0, 5, 1.0, 0, '{"dialog": "I sell the finest weapons and armor! Come back when you have gold."}'),

-- Monsters - Orcs
('Orc Warrior 1', 'monster', 400, 300, 400, 300, 50, 50, 0, 0, 12, 3, 1.0, 300, '{"type": "orc", "aggressive": "true"}'),
('Orc Warrior 2', 'monster', 500, 300, 500, 300, 50, 50, 0, 0, 12, 3, 1.0, 300, '{"type": "orc", "aggressive": "true"}'),
('Orc Warrior 3', 'monster', 600, 300, 600, 300, 50, 50, 0, 0, 12, 3, 1.0, 300, '{"type": "orc", "aggressive": "true"}'),
('Orc Warrior 4', 'monster', 700, 300, 700, 300, 50, 50, 0, 0, 12, 3, 1.0, 300, '{"type": "orc", "aggressive": "true"}'),
('Orc Warrior 5', 'monster', 800, 300, 800, 300, 50, 50, 0, 0, 12, 3, 1.0, 300, '{"type": "orc", "aggressive": "true"}'),

-- Monsters - Trolls
('Troll 1', 'monster', 300, 200, 300, 200, 100, 100, 20, 20, 20, 8, 0.8, 600, '{"type": "troll", "aggressive": "true"}'),
('Troll 2', 'monster', 450, 200, 450, 200, 100, 100, 20, 20, 20, 8, 0.8, 600, '{"type": "troll", "aggressive": "true"}'),
('Troll 3', 'monster', 600, 200, 600, 200, 100, 100, 20, 20, 20, 8, 0.8, 600, '{"type": "troll", "aggressive": "true"}'),

-- Items
('Health Potion', 'item', 550, 450, 550, 450, 1, 1, 0, 0, 0, 0, 0, 0, '{"type": "consumable", "effect": "heal", "value": "25"}'),
('Mana Potion', 'item', 570, 450, 570, 450, 1, 1, 0, 0, 0, 0, 0, 0, '{"type": "consumable", "effect": "mana", "value": "15"}'),
('Sword', 'item', 650, 480, 650, 480, 1, 1, 0, 0, 0, 0, 0, 0, '{"type": "weapon", "attack_bonus": "5", "description": "A sturdy iron sword"}')

ON CONFLICT ("Id") DO NOTHING;

-- Seeds de itens iniciais (expostos no mundo - posições definidas)
INSERT INTO "Items" ("Name", "item_type", "Description", "Sprite", "Quantity", "PositionX", "PositionY") VALUES
('Health Potion', 'health_potion', 'Restores a small amount of health.', 'health_potion_sprite', 1, 550, 450),
('Mana Potion', 'mana_potion', 'Restores a small amount of mana.', 'mana_potion_sprite', 1, 570, 450),
('Sword', 'sword', 'A sturdy iron sword', 'sword_sprite', 1, 650, 480)
ON CONFLICT DO NOTHING;

-- Vincular WorldEntities de itens às linhas de Items (caso ainda não vinculadas)
UPDATE "WorldEntities" w
SET "ItemId" = i."Id"
FROM "Items" i
WHERE w."EntityType" = 'item'
  AND w."ItemId" IS NULL
  AND w."Name" = i."Name"
  AND w."PositionX" = i."PositionX"
  AND w."PositionY" = i."PositionY";

-- Fallback: criar WorldEntities para quaisquer Items que não possuam WorldEntity associada
INSERT INTO "WorldEntities" (
    "Id","Name","EntityType","PositionX","PositionY","SpawnX","SpawnY",
    "CurrentHp","MaxHp","CurrentMp","MaxMp","Attack","Defense","Speed",
    "MovementState","FacingDirection","IsAlive","RespawnDelaySeconds","Properties","ItemId"
)
SELECT gen_random_uuid(), i."Name", 'item', COALESCE(i."PositionX",0), COALESCE(i."PositionY",0), COALESCE(i."PositionX",0), COALESCE(i."PositionY",0),
       1,1,0,0,0,0,0,'idle',0,true,0,'{}', i."Id"
FROM "Items" i
LEFT JOIN "WorldEntities" w ON w."ItemId" = i."Id"
WHERE w."ItemId" IS NULL;

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'Game Server database initialized successfully!';
END $$;
