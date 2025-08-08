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

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS "IX_Accounts_Email" ON "Accounts" ("Email");
CREATE INDEX IF NOT EXISTS "IX_Players_AccountId" ON "Players" ("AccountId");
CREATE INDEX IF NOT EXISTS "IX_Players_Name" ON "Players" ("Name");
CREATE INDEX IF NOT EXISTS "IX_ActiveTokens_AccountId" ON "ActiveTokens" ("AccountId");
CREATE INDEX IF NOT EXISTS "IX_ActiveTokens_Expires" ON "ActiveTokens" ("Expires");

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

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'Game Server database initialized successfully!';
END $$;
