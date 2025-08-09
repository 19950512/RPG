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
    "LastUpdate" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ActiveTokens table
CREATE TABLE IF NOT EXISTS "ActiveTokens" (
    "Id" SERIAL PRIMARY KEY,
    "AccountId" UUID NOT NULL REFERENCES "Accounts"("Id") ON DELETE CASCADE,
    "Token" TEXT NOT NULL,
    "Expires" TIMESTAMP WITH TIME ZONE NOT NULL
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

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS "IX_Accounts_Email" ON "Accounts" ("Email");
CREATE INDEX IF NOT EXISTS "IX_Players_AccountId" ON "Players" ("AccountId");
CREATE INDEX IF NOT EXISTS "IX_Players_Name" ON "Players" ("Name");
CREATE INDEX IF NOT EXISTS "IX_ActiveTokens_AccountId" ON "ActiveTokens" ("AccountId");
CREATE INDEX IF NOT EXISTS "IX_ActiveTokens_Expires" ON "ActiveTokens" ("Expires");
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

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'Game Server database initialized successfully!';
END $$;
