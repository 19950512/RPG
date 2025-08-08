-- Script para marcar personagem como online e testar movimento
-- Usado como workaround temporário enquanto JoinWorld não funciona

-- Marcar o último personagem criado como online
UPDATE "Players" 
SET "IsOnline" = true, "LastUpdate" = NOW()
WHERE "Id" = (
    SELECT "Id" 
    FROM "Players" 
    ORDER BY "Id" DESC 
    LIMIT 1
);

-- Verificar se foi atualizado
SELECT "Name", "Vocation", "IsOnline", "PositionX", "PositionY", "LastUpdate"
FROM "Players" 
WHERE "IsOnline" = true
ORDER BY "LastUpdate" DESC;
