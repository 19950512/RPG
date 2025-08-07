#!/usr/bin/env python3
import bcrypt

# Gerar hash para "password123"
password = "password123"
hash_bytes = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
hash_str = hash_bytes.decode('utf-8')

print(f"Senha: {password}")
print(f"Hash: {hash_str}")

# Verificar se o hash funciona
if bcrypt.checkpw(password.encode('utf-8'), hash_bytes):
    print("✓ Hash verificado com sucesso!")
else:
    print("✗ Falha na verificação do hash")
