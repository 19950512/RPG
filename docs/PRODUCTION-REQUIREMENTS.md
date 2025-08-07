# Requisitos de Memória para Produção - Game Server

## 📊 Estimativa de Recursos (VPS)

### 🎯 **Configuração Mínima Recomendada**
- **RAM**: 4GB
- **CPU**: 2 vCPUs  
- **Disco**: 40GB SSD
- **Bandwidth**: 1TB/mês

### 🚀 **Configuração Recomendada para Performance**
- **RAM**: 8GB
- **CPU**: 4 vCPUs
- **Disco**: 80GB SSD
- **Bandwidth**: 2TB/mês

### 🏆 **Configuração Enterprise (Alta Carga)**
- **RAM**: 16GB+
- **CPU**: 8+ vCPUs
- **Disco**: 160GB+ SSD
- **Bandwidth**: 5TB+/mês

## 🔍 **Breakdown de Memória por Serviço**

### Game Server (.NET 8)
- **Base**: ~200MB
- **Por 1000 conexões**: ~100MB
- **Cache de objetos**: ~50MB
- **Total estimado**: 350-500MB

### PostgreSQL
- **Base**: ~50MB
- **shared_buffers**: 256MB (configurado)
- **Cache**: 1GB (effective_cache_size)
- **Conexões**: ~2MB por 100 conexões
- **Total estimado**: 800MB-1.2GB

### Redis
- **Base**: ~20MB
- **Cache configurado**: 512MB (maxmemory)
- **Total estimado**: 532MB

### Nginx
- **Base**: ~10MB
- **Buffer/cache**: ~50MB
- **Total estimado**: 60MB

### Sistema Operacional (Linux)
- **Kernel + serviços**: ~300-500MB

## 📈 **Cálculo por Número de Jogadores**

### 1.000 jogadores simultâneos
- **RAM Total**: 3GB
- **Recomendado**: 4GB VPS

### 10.000 jogadores simultâneos  
- **RAM Total**: 5-6GB
- **Recomendado**: 8GB VPS

### 100.000 jogadores simultâneos
- **RAM Total**: 12-15GB
- **Recomendado**: 16GB+ VPS + Load Balancing

## ⚙️ **Otimizações para Reduzir Uso de Memória**

### 1. Configurações PostgreSQL Otimizadas
```sql
shared_buffers = 256MB          # 25% da RAM disponível
effective_cache_size = 1GB      # 70% da RAM disponível  
work_mem = 4MB                  # Por consulta
maintenance_work_mem = 64MB     # Para operações de manutenção
```

### 2. Configurações .NET
```csharp
// Garbage Collection otimizado
"System.GC.Server": true,
"System.GC.Concurrent": true,
"System.GC.RetainVM": true
```

### 3. Redis Cache Policy
```
maxmemory 512mb
maxmemory-policy allkeys-lru
```

## 🌐 **Providers VPS Recomendados**

### Nacional (Brasil)
- **UOLHost**: 4GB RAM / 2 vCPU - ~R$ 80/mês
- **Locaweb**: 4GB RAM / 2 vCPU - ~R$ 90/mês
- **KingHost**: 4GB RAM / 2 vCPU - ~R$ 85/mês

### Internacional
- **DigitalOcean**: 4GB RAM / 2 vCPU - $24/mês
- **Linode**: 4GB RAM / 2 vCPU - $24/mês
- **Vultr**: 4GB RAM / 2 vCPU - $24/mês

### Cloud Premium
- **AWS EC2**: t3.medium (4GB/2vCPU) - ~$35/mês
- **Google Cloud**: e2-medium (4GB/2vCPU) - ~$35/mês
- **Azure**: B2s (4GB/2vCPU) - ~$35/mês

## 📋 **Monitoramento de Recursos**

### Métricas Importantes
```bash
# Uso de memória
docker stats

# Conexões ativas no PostgreSQL
SELECT count(*) FROM pg_stat_activity;

# Uso de cache Redis
INFO memory

# Conexões gRPC ativas
netstat -an | grep :5001 | wc -l
```

### Alertas Recomendados
- **RAM > 80%**: Considerar upgrade
- **CPU > 70%**: Investigar bottlenecks
- **Disk > 85%**: Limpeza de logs
- **Network > 80%**: Monitorar DDoS

## 🎯 **Recomendação Final**

Para começar em produção com até **5.000 jogadores simultâneos**:

**VPS de 8GB RAM / 4 vCPUs / 80GB SSD**

Isso garante:
- ✅ Margem de segurança para picos de uso
- ✅ Espaço para crescimento orgânico  
- ✅ Performance estável
- ✅ Custo-benefício adequado (~$40-50/mês)

Com essa configuração você pode escalar horizontalmente quando necessário!
