#!/usr/bin/env python3
"""
Script para gerar arquivos Python a partir dos arquivos .proto
"""

import os
import subprocess
import sys
from pathlib import Path

def run_command(cmd, cwd=None):
    """Executa um comando e retorna o resultado"""
    print(f"🔄 Executando: {' '.join(cmd)}")
    if cwd:
        print(f"   📁 Diretório: {cwd}")
    
    try:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True)
        if result.stdout.strip():
            print(f"   ✅ Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Erro: {e}")
        if e.stdout:
            print(f"   📤 stdout: {e.stdout}")
        if e.stderr:
            print(f"   📥 stderr: {e.stderr}")
        return False

def main():
    # Caminhos
    project_root = Path(__file__).parent
    client_dir = project_root / "src" / "GameClient"
    protos_dir = client_dir / "Protos"
    generated_dir = client_dir / "Generated"
    
    print(f"🚀 Gerando arquivos Python a partir dos .proto files")
    print(f"📁 Projeto: {project_root}")
    print(f"📁 Protos: {protos_dir}")
    print(f"📁 Generated: {generated_dir}")
    
    # Verificar se os diretórios existem
    if not protos_dir.exists():
        print(f"❌ Diretório de protos não encontrado: {protos_dir}")
        return False
    
    # Criar diretório Generated se não existir
    generated_dir.mkdir(exist_ok=True)
    
    # Criar __init__.py no diretório Generated se não existir
    init_file = generated_dir / "__init__.py"
    if not init_file.exists():
        init_file.write_text("")
        print(f"✅ Criado: {init_file}")
    
    # Buscar todos os arquivos .proto
    proto_files = list(protos_dir.glob("*.proto"))
    if not proto_files:
        print(f"❌ Nenhum arquivo .proto encontrado em {protos_dir}")
        return False
    
    print(f"📋 Arquivos .proto encontrados:")
    for proto_file in proto_files:
        print(f"   📄 {proto_file.name}")
    
    # Instalar dependências necessárias
    print("🔧 Verificando e instalando dependências...")
    dependencies = [
        "grpcio-tools",
        "grpcio", 
        "protobuf"
    ]
    
    for dep in dependencies:
        print(f"📦 Instalando {dep}...")
        # Tentar instalar com --break-system-packages para ambientes gerenciados
        if not run_command([sys.executable, "-m", "pip", "install", "--break-system-packages", dep]):
            print(f"❌ Falha ao instalar {dep}")
            return False
    
    # Verificar se grpc_tools.protoc está disponível
    try:
        result = subprocess.run([sys.executable, "-m", "grpc_tools.protoc", "--version"], 
                              capture_output=True, check=True)
        print("✅ grpc_tools.protoc encontrado")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ grpc_tools.protoc não encontrado mesmo após instalação")
        return False
    
    # Gerar arquivos para cada .proto
    success = True
    for proto_file in proto_files:
        print(f"\n🔄 Processando {proto_file.name}...")
        
        # Comando para gerar arquivos _pb2.py e _pb2_grpc.py
        cmd = [
            sys.executable, "-m", "grpc_tools.protoc",
            f"--proto_path={protos_dir}",
            f"--python_out={generated_dir}",
            f"--grpc_python_out={generated_dir}",
            str(proto_file)
        ]
        
        if not run_command(cmd):
            success = False
            continue
        
        # Verificar se os arquivos foram gerados
        base_name = proto_file.stem
        pb2_file = generated_dir / f"{base_name}_pb2.py"
        grpc_file = generated_dir / f"{base_name}_pb2_grpc.py"
        
        if pb2_file.exists():
            print(f"   ✅ Gerado: {pb2_file.name}")
        else:
            print(f"   ❌ Não gerado: {pb2_file.name}")
            success = False
            
        if grpc_file.exists():
            print(f"   ✅ Gerado: {grpc_file.name}")
        else:
            print(f"   ❌ Não gerado: {grpc_file.name}")
            success = False
    
    if success:
        print(f"\n🎉 Todos os arquivos foram gerados com sucesso em {generated_dir}")
        
        # Listar arquivos gerados
        generated_files = list(generated_dir.glob("*.py"))
        print(f"\n📋 Arquivos gerados:")
        for file in sorted(generated_files):
            print(f"   📄 {file.name}")
    else:
        print(f"\n❌ Alguns arquivos falharam ao gerar")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
