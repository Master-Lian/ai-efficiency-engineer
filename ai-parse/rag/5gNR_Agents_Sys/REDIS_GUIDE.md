# Redis 在 5G NR 多智能体协同保障系统中的应用

## 目录

- [Redis 基础知识](#redis-基础知识)
- [Redis 在项目中的应用场景](#redis-在项目中的应用场景)
- [项目中的 Redis 配置](#项目中的-redis-配置)
- [Redis 数据结构选择](#redis-数据结构选择)
- [Redis 与其他方案的对比](#redis-与其他方案的对比)
- [面试问答](#面试问答)

---

## Redis 基础知识

### 1. 什么是 Redis？

Redis（Remote Dictionary Server）是一个开源的**内存数据库**，也称为**数据结构服务器**。

| 特性 | 说明 |
|------|------|
| **内存存储** | 所有数据存储在内存中，读写速度极快 |
| **数据结构丰富** | String、Hash、List、Set、ZSet、Stream 等 |
| **持久化** | 支持 RDB 和 AOF 两种持久化方式 |
| **高可用** | 支持主从复制、哨兵模式、集群模式 |
| **单线程模型** | 避免锁竞争，性能优异 |

### 2. Redis 的核心数据结构

| 数据结构 | 用途 | 示例 |
|---------|------|------|
| **String** | 缓存、计数器 | `SET key value`、`INCR key` |
| **Hash** | 对象存储 | `HSET user:1 name "张三"` |
| **List** | 队列、栈 | `LPUSH queue task`、`RPOP queue` |
| **Set** | 去重、交集 | `SADD tags "python"` |
| **ZSet** | 排行榜、限流 | `ZADD ranking 100 user1` |
| **Stream** | 消息队列 | `XADD stream * field value` |

### 3. Redis 的性能指标

| 指标 | 数值 | 说明 |
|------|------|------|
| **QPS** | 10万+ | 单实例每秒可处理 10 万次查询 |
| **延迟** | < 1ms | 内存读写延迟通常在 1ms 以内 |
| **吞吐量** | GB/s | 网络带宽是主要瓶颈 |

---

## Redis 在项目中的应用场景

### 场景 1：智能体间通信

#### 问题描述

三个智能体（感知、决策、执行）需要协同工作，如何高效通信？

#### 解决方案

使用 Redis 作为**消息总线**，实现智能体间的异步通信。

```python
# 感知智能体：发布指标数据
def publish_metrics(metrics: Dict[str, Any]):
    redis_client.publish("metrics:stream", json.dumps(metrics))

# 决策智能体：订阅指标数据
def subscribe_metrics():
    pubsub = redis_client.pubsub()
    pubsub.subscribe("metrics:stream")
    for message in pubsub.listen():
        process_metrics(json.loads(message["data"]))
```

#### 数据结构选择

| 数据结构 | 选择原因 |
|---------|---------|
| **Pub/Sub** | 一对多广播，适合指标分发 |
| **Stream** | 消息持久化，支持回放 |

---

### 场景 2：缓存 RAG 检索结果

#### 问题描述

RAG 检索耗时较长（200-500ms），如何优化？

#### 解决方案

使用 Redis 缓存检索结果，相同查询直接返回。

```python
def rag_retrieve(query: str) -> Dict[str, Any]:
    cache_key = f"rag:{hashlib.md5(query.encode()).hexdigest()}"
    
    # 1. 尝试从缓存获取
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # 2. 执行 RAG 检索
    result = bm25_search(query) + faiss_search(query)
    
    # 3. 写入缓存（过期时间 1 小时）
    redis_client.setex(cache_key, 3600, json.dumps(result))
    
    return result
```

#### 数据结构选择

| 数据结构 | 选择原因 |
|---------|---------|
| **String** | 简单键值对，适合缓存 |
| **EXPIRE** | 自动过期，避免数据过期 |

---

### 场景 3：缓存历史诊断结果

#### 问题描述

相同故障重复出现，如何避免重复调用 LLM？

#### 解决方案

使用 Redis 缓存历史诊断结果，相似故障直接返回。

```python
def diagnose_fault(fault_signature: str) -> Dict[str, Any]:
    cache_key = f"diagnosis:{fault_signature}"
    
    # 1. 检查缓存
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # 2. 调用 LLM 诊断
    diagnosis = llm_diagnose(fault_signature)
    
    # 3. 写入缓存（过期时间 24 小时）
    redis_client.setex(cache_key, 86400, json.dumps(diagnosis))
    
    return diagnosis
```

#### 故障签名生成

```python
def generate_fault_signature(metrics: Dict[str, Any]) -> str:
    """生成故障签名，用于缓存键"""
    key_fields = ["rsrp", "sinr", "packet_loss", "fault_type"]
    signature = ":".join([str(metrics.get(k, "")) for k in key_fields])
    return hashlib.md5(signature.encode()).hexdigest()
```

---

### 场景 4：存储智能体状态

#### 问题描述

智能体重启后如何恢复之前的状态？

#### 解决方案

使用 Redis 持久化智能体运行状态。

```python
def save_agent_state(agent_name: str, state: Dict[str, Any]):
    """保存智能体状态"""
    redis_client.hset(f"agent:{agent_name}", mapping=state)
    redis_client.expire(f"agent:{agent_name}", 86400)  # 24 小时过期

def load_agent_state(agent_name: str) -> Dict[str, Any]:
    """加载智能体状态"""
    state = redis_client.hgetall(f"agent:{agent_name}")
    return {k.decode(): v.decode() for k, v in state.items()} if state
```

#### 数据结构选择

| 数据结构 | 选择原因 |
|---------|---------|
| **Hash** | 存储对象的多个字段，方便部分更新 |

---

### 场景 5：分布式锁

#### 问题描述

多个智能体同时操作同一设备，如何避免冲突？

#### 解决方案

使用 Redis 分布式锁。

```python
def acquire_lock(device_id: str, timeout: int = 10) -> bool:
    """获取分布式锁"""
    lock_key = f"lock:device:{device_id}"
    lock_value = str(uuid.uuid4())
    
    # 尝试获取锁（SET NX EX）
    acquired = redis_client.set(lock_key, lock_value, nx=True, ex=timeout)
    return bool(acquired)

def release_lock(device_id: str, lock_value: str):
    """释放分布式锁"""
    lock_key = f"lock:device:{device_id}"
    # 使用 Lua 脚本确保原子性
    script = """
    if redis.call("get", KEYS[1]) == ARGV[1] then
        return redis.call("del", KEYS[1])
    else
        return 0
    end
    """
    redis_client.eval(script, 1, lock_key, lock_value)
```

#### 使用示例

```python
def execute_action(device_id: str, action: Dict):
    """执行设备操作（带锁）"""
    lock_value = str(uuid.uuid4())
    
    if acquire_lock(device_id):
        try:
            # 执行操作
            result = apply_action(device_id, action)
            return result
        finally:
            release_lock(device_id, lock_value)
    else:
        raise Exception("设备被其他智能体占用")
```

---

## 项目中的 Redis 配置

### 1. 配置文件

```python
# core/config.py
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
```

### 2. K8s 部署配置

```yaml
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: 5g-nr-config
data:
  REDIS_URL: "redis://redis-service:6379"
```

```yaml
# k8s/deployment.yaml（Redis 服务）
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
```

### 3. Redis 连接池

```python
import redis
from redis.connection import ConnectionPool

# 创建连接池
pool = ConnectionPool.from_url(
    "redis://localhost:6379",
    max_connections=50,
    decode_responses=True  # 自动解码为字符串
)

# 创建 Redis 客户端
redis_client = redis.Redis(connection_pool=pool)
```

---

## Redis 数据结构选择

### 选择决策树

```
需求
  │
  ├─ 需要持久化？
  │   ├─ 是 → 使用 Hash 或 String
  │   └─ 否 → 继续
  │
  ├─ 需要排序？
  │   ├─ 是 → 使用 ZSet
  │   └─ 否 → 继续
  │
  ├─ 需要去重？
  │   ├─ 是 → 使用 Set
  │   └─ 否 → 继续
  │
  ├─ 需要队列？
  │   ├─ 是 → 使用 List 或 Stream
  │   └─ 否 → 继续
  │
  └─ 简单键值对？
      ├─ 是 → 使用 String
      └─ 否 → 使用 Hash
```

### 项目中的数据结构映射

| 场景 | 数据结构 | 键命名规范 | 过期时间 |
|------|---------|------------|---------|
| 智能体通信 | Pub/Sub | `metrics:stream` | 不过期 |
| RAG 缓存 | String | `rag:{query_hash}` | 1 小时 |
| 诊断缓存 | String | `diagnosis:{fault_sig}` | 24 小时 |
| 智能体状态 | Hash | `agent:{agent_name}` | 24 小时 |
| 分布式锁 | String | `lock:device:{device_id}` | 10 秒 |

---

## Redis 与其他方案的对比

### 1. Redis vs Memcached

| 特性 | Redis | Memcached |
|------|--------|-----------|
| 数据结构 | 丰富（5+ 种） | 仅 String |
| 持久化 | 支持 | 不支持 |
| 分布式 | 支持 | 支持 |
| 内存管理 | LRU/LFU | LRU |
| 适用场景 | 复杂数据、持久化 | 简单缓存 |

**结论**：项目选择 Redis 是因为需要 Hash、ZSet 等复杂数据结构。

### 2. Redis vs Kafka

| 特性 | Redis | Kafka |
|------|--------|-------|
| 消息持久化 | 支持（Stream） | 支持 |
| 吞吐量 | 10 万 QPS | 100 万 msg/s |
| 延迟 | < 1ms | 10-50ms |
| 复杂度 | 简单 | 复杂 |
| 适用场景 | 实时通信、缓存 | 大数据流、日志 |

**结论**：项目使用 Redis 作为消息总线，如果数据量增长到 GB 级别，可以迁移到 Kafka。

### 3. Redis vs 数据库（MySQL/PostgreSQL）

| 特性 | Redis | MySQL |
|------|--------|-------|
| 存储介质 | 内存 | 磁盘 |
| 读写速度 | 极快 | 较慢 |
| 数据结构 | 丰富 | 关系表 |
| 持久化 | 可选 | 原生支持 |
| 适用场景 | 缓存、会话 | 持久化数据 |

**结论**：Redis 用于缓存和实时通信，MySQL 用于持久化存储（如历史工单）。

---

## 面试问答

### Q1：为什么选择 Redis 而不是其他方案？

**答**：
1. **性能**：内存存储，读写延迟 < 1ms，满足实时性要求
2. **数据结构丰富**：支持 Pub/Sub、Hash、Stream 等，适合多种场景
3. **简单易用**：API 简洁，部署方便
4. **生态成熟**：Python 客户端稳定，K8s 支持完善

### Q2：Redis 的数据如何保证一致性？

**答**：
1. **单线程模型**：避免并发写入冲突
2. **原子操作**：使用 Lua 脚本保证多步操作的原子性
3. **分布式锁**：防止多个智能体同时操作同一资源
4. **过期策略**：设置合理的过期时间，避免脏数据

### Q3：Redis 挂了怎么办？

**答**：
1. **降级策略**：切换到本地缓存或直接调用后端服务
2. **重试机制**：指数退避重试（1s, 2s, 4s, 8s）
3. **告警通知**：发送告警，运维人员介入
4. **数据恢复**：Redis 恢复后，重新加载智能体状态

```python
def redis_with_fallback():
    try:
        return redis_client.get(key)
    except redis.ConnectionError:
        logger.warning("Redis 不可用，使用降级策略")
        return local_cache.get(key, None)
```

### Q4：如何监控 Redis 的性能？

**答**：
1. **INFO 命令**：`redis-cli INFO` 获取内存、连接数、QPS 等
2. **Prometheus + Grafana**：使用 redis-exporter 采集指标
3. **慢查询日志**：配置 `slowlog-log-slower-than` 记录慢查询
4. **告警规则**：内存使用率 > 80%、连接数 > 1000 时告警

### Q5：Redis 的内存如何优化？

**答**：
1. **设置过期时间**：所有缓存数据设置合理的 TTL
2. **使用 Hash**：多个字段合并存储，减少键数量
3. **压缩数据**：JSON 数据压缩后存储
4. **选择合适的数据结构**：如用 ZSet 替代 List + 排序
5. **内存淘汰策略**：配置 `maxmemory-policy` 为 `allkeys-lru`

```python
# 压缩示例
import gzip
import json

data = {"key": "value", "key2": "value2"}
compressed = gzip.compress(json.dumps(data).encode())
redis_client.set("key", compressed)
```

### Q6：Redis 的分布式锁怎么实现？

**答**：使用 `SET NX EX` 命令实现：

```python
def acquire_lock(key: str, value: str, expire: int = 10) -> bool:
    """获取锁"""
    return redis_client.set(key, value, nx=True, ex=expire)

def release_lock(key: str, value: str):
    """释放锁（使用 Lua 脚本保证原子性）"""
    script = """
    if redis.call("get", KEYS[1]) == ARGV[1] then
        return redis.call("del", KEYS[1])
    else
        return 0
    end
    """
    return redis_client.eval(script, 1, key, value)
```

关键点：
- `nx=True`：只有键不存在时才设置
- `ex=expire`：设置过期时间，避免死锁
- Lua 脚本：保证"检查+删除"的原子性

### Q7：Redis 的 Pub/Sub 和 Stream 有什么区别？

**答**：

| 特性 | Pub/Sub | Stream |
|------|----------|---------|
| 消息持久化 | 不持久化 | 持久化 |
| 消费者 | 在线才能收到 | 可以回溯历史消息 |
| 消息确认 | 不支持 | 支持（ACK） |
| 适用场景 | 实时通知 | 消息队列 |

**项目选择**：
- **Pub/Sub**：用于实时指标分发（在线消费者）
- **Stream**：用于消息队列（需要持久化）

---

## 总结

### Redis 在项目中的核心价值

| 价值 | 说明 |
|------|------|
| **性能提升**：缓存 RAG 结果，减少 LLM 调用，响应时间从 500ms 降到 5ms |
| **解耦智能体**：通过 Pub/Sub 实现异步通信，智能体独立部署 |
| **状态恢复**：持久化智能体状态，重启后自动恢复 |
| **并发控制**：分布式锁避免资源冲突 |

### 学习建议

1. **基础**：掌握 5 种数据结构（String、Hash、List、Set、ZSet）
2. **进阶**：理解 Pub/Sub、Stream、分布式锁
3. **实战**：在项目中实际应用，观察性能提升
4. **优化**：学习内存优化、持久化、集群配置

### 推荐资源

- [Redis 官方文档](https://redis.io/docs/)
- [Redis 命令参考](https://redis.io/commands/)
- [Python 客户端文档](https://redis-py.readthedocs.io/)
