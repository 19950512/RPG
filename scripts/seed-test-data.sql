-- Script para inserir dados de teste no GameServer
-- Este script cria contas e personagens de teste para desenvolvimento

-- Inserir conta de teste (senha: "password123" - hash bcrypt)
INSERT INTO "Accounts" ("Id", "Email", "PasswordHash", "IsActive", "CreatedAt") 
VALUES (
    gen_random_uuid(),
    'test@gameserver.com',
    '$2a$11$3WUFO1lA0aMJxTLJw/V4jOKjQy.9dZyq5FHRfxHHYzq1lCx3w2I3G', -- "password123"
    true,
    NOW()
) ON CONFLICT ("Email") DO NOTHING;

-- Inserir conta admin de teste (senha: "admin123")
INSERT INTO "Accounts" ("Id", "Email", "PasswordHash", "IsActive", "CreatedAt") 
VALUES (
    gen_random_uuid(),
    'admin@gameserver.com',
    '$2a$11$jX8dZyq5FHRfxHHYzq1lCx3w2I3G3WUFO1lA0aMJxTLJw/V4jOKjQy', -- "admin123"
    true,
    NOW()
) ON CONFLICT ("Email") DO NOTHING;

-- Inserir personagens de teste para a conta test@gameserver.com
DO $$
DECLARE
    test_account_id UUID;
BEGIN
    -- Buscar o ID da conta de teste
    SELECT "Id" INTO test_account_id 
    FROM "Accounts" 
    WHERE "Email" = 'test@gameserver.com';
    
    -- Inserir personagens de teste
    IF test_account_id IS NOT NULL THEN
        INSERT INTO "Players" (
            "Id", "AccountId", "Name", "Vocation", "Experience", "Level",
            "PositionX", "PositionY", "CurrentHp", "MaxHp", "CurrentMp", "MaxMp",
            "Attack", "Defense", "Speed", "MovementState", "FacingDirection", "IsOnline"
        ) VALUES 
        (
            gen_random_uuid(),
            test_account_id,
            'TestKnight',
            'Knight',
            1000,
            10,
            100.0, 100.0, -- Posição inicial
            150, 150, -- HP
            50, 50,   -- MP
            25, 20, 100.0, -- Attack, Defense, Speed
            'idle',
            2, -- South direction
            false
        ),
        (
            gen_random_uuid(),
            test_account_id,
            'TestMage',
            'Mage',
            800,
            8,
            150.0, 150.0, -- Posição inicial
            80, 80,   -- HP
            120, 120, -- MP
            15, 10, 100.0, -- Attack, Defense, Speed
            'idle',
            0, -- North direction
            false
        ) ON CONFLICT ("Name") DO NOTHING;
    END IF;
END $$;

-- Mostrar dados inseridos
SELECT 'Accounts created:' as info;
SELECT "Email", "IsActive", "CreatedAt" FROM "Accounts" WHERE "Email" LIKE '%gameserver.com';

SELECT 'Players created:' as info;
SELECT p."Name", p."Vocation", p."Level", a."Email" 
FROM "Players" p 
JOIN "Accounts" a ON p."AccountId" = a."Id"
WHERE a."Email" LIKE '%gameserver.com';
