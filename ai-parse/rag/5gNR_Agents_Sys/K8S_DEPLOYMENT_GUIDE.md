# 5G NR Agents System - Kubernetes 部署与使用手册

## 目录

- [项目概述](#项目概述)
- [系统架构](#系统架构)
- [环境准备](#环境准备)
- [K8s 配置文件说明](#k8s-配置文件说明)
- [部署步骤](#部署步骤)
- [运行与验证](#运行与验证)
- [日常运维](#日常运维)
- [监控与日志](#监控与日志)
- [故障排查](#故障排查)
- [常见问题](#常见问题)

---

## 项目概述

### 简介

5G NR Agents System 是一个基于多智能体协同的 5G 网络自动化运维系统，实现"秒级感知 → 自动诊断 → 智能决策 → 快速执行"的全流程自动化。

### 核心功能

| 模块 | 功能描述 |
|------|---------|
| 感知智能体 | 实时采集 5G 网络指标（RSRP、SINR、吞吐量等） |
| 决策智能体 | 基于 RAG 混合检索和 LLM 进行故障诊断 |
| 执行智能体 | 自动执行修复操作并提供回滚能力 |
| 四层防护 | 诊断验证、安全检查、效果验证、回滚管理 |

### 技术栈

- Python 3.10
- LangChain / LangGraph
- ChromaDB / FAISS
- DeepSeek API
- Kubernetes

---

## 系统架构

### 目录结构

```
5gNR_Agents_Sys/
├── agents/                 # 智能体模块
│   ├── percept_agent.py    # 感知智能体
│   ├── decision_agent.py   # 决策智能体
│   ├── exec_agent.py       # 执行智能体
│   └── qa_agent.py         # 问答智能体
├── core/                   # 核心模块
│   ├── config.py           # 全局配置
│   ├── base_skill.py       # 技能基类
│   ├── diagnosis_validator.py   # 诊断验证器
│   ├── safety_checker.py        # 安全检查器
│   ├── effect_verifier.py       # 效果验证器
│   └── rollback_manager.py      # 回滚管理器
├── skills/                 # 原子技能
│   ├── metric_collect.py   # 指标采集
│   ├── fault_detect.py     # 故障检测
│   ├── rag_retrieve.py     # RAG 检索
│   ├── diagnose.py         # 故障诊断
│   ├── execute.py          # 自愈执行
│   └── qa_rag.py           # RAG 问答
├── mcp/                    # MCP 调度中心
│   └── scheduler.py        # 调度器
├── data/                   # 知识库数据
│   └── 5g_knowledge.md     # 5G 运维知识库
├── tests/                  # 测试用例
├── k8s/                    # K8s 部署配置
├── Dockerfile              # Docker 镜像构建
├── requirements.txt        # Python 依赖
├── deploy.sh               # 部署脚本
└── main.py                 # 系统入口
```

---

## 环境准备

### 前置要求

| 工具 | 版本要求 | 用途 |
|------|---------|------|
| Docker | 20.10+ | 容器构建与运行 |
| kubectl | 1.24+ | K8s 命令行工具 |
| Kubernetes | 1.24+ | 容器编排平台 |
| Git | 2.30+ | 代码管理 |

### 本地开发环境

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 设置环境变量
export DEEPSEEK_API_KEY="your-api-key-here"

# 本地运行
python main.py
```

### K8s 集群选项

| 环境 | 适用场景 | 命令 |
|------|---------|------|
| Minikube | 本地开发测试 | `minikube start` |
| Kind | 本地多节点集群 | `kind create cluster` |
| Docker Desktop | Mac/Windows 开发 | 启用 Kubernetes |
| 云服务商 | 生产环境 | AWS EKS / GCP GKE / Azure AKS |

---

## K8s 配置文件说明

### k8s/namespace.yaml

创建独立的命名空间隔离资源：

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: 5g-nr-agents
```

### k8s/configmap.yaml

管理应用配置（非敏感信息）：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| MODEL_NAME | deepseek-chat | LLM 模型名称 |
| KNOWLEDGE_BASE | /app/data/5g_knowledge.md | 知识库路径 |
| PERSIST_DIR | /app/data/chroma_db | 向量数据库路径 |
| EMBEDDING_MODEL | sentence-transformers/all-MiniLM-L6-v2 | 嵌入模型 |
| RETRIEVAL_K | 3 | 检索返回文档数 |
| CHUNK_SIZE | 1000 | 文本分块大小 |
| CHUNK_OVERLAP | 100 | 分块重叠大小 |
| SIMILARITY_THRESHOLD | 0.5 | 相似度阈值 |
| LOG_LEVEL | INFO | 日志级别 |

### k8s/secret.yaml

管理敏感信息（API 密钥等）：

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: 5g-nr-secret
  namespace: 5g-nr-agents
type: Opaque
stringData:
  DEEPSEEK_API_KEY: "your-api-key-here"  # 修改为真实 API Key
```

### k8s/deployment.yaml

定义应用部署配置：

| 配置项 | 值 | 说明 |
|--------|---|------|
| replicas | 3 | 初始副本数 |
| maxSurge | 1 | 滚动更新时最大新增 Pod 数 |
| maxUnavailable | 0 | 滚动更新时最大不可用 Pod 数 |
| CPU 请求 | 1000m | 每个 Pod 请求的 CPU |
| CPU 限制 | 2000m | 每个 Pod 最大 CPU |
| 内存请求 | 2Gi | 每个 Pod 请求的内存 |
| 内存限制 | 4Gi | 每个 Pod 最大内存 |
| 健康检查 | /health:8000 | HTTP 健康检查端点 |

### k8s/service.yaml

定义服务暴露方式：

- 类型：ClusterIP（集群内部访问）
- 端口：80 → 8000

### k8s/ingress.yaml

定义外部访问规则（可选）：

- 需要配置域名和 TLS 证书
- 使用 Nginx Ingress Controller

### k8s/pvc.yaml

定义持久化存储：

- 大小：10Gi
- 访问模式：ReadWriteOnce

### k8s/hpa.yaml

定义自动扩缩容：

| 配置项 | 值 |
|--------|---|
| 最小副本数 | 2 |
| 最大副本数 | 10 |
| CPU 目标利用率 | 70% |
| 内存目标利用率 | 80% |

---

## 部署步骤

### 第一步：修改配置

编辑 `k8s/secret.yaml`，替换 API Key：

```yaml
stringData:
  DEEPSEEK_API_KEY: "sk-your-actual-api-key-here"
```

### 第二步：构建镜像

```bash
# 进入项目目录
cd 5gNR_Agents_Sys

# 构建 Docker 镜像
docker build -t 5g-nr-agent-system:latest .
```

### 第三步：加载镜像（本地 K8s）

```bash
# Minikube
minikube image load 5g-nr-agent-system:latest

# Kind
kind load docker-image 5g-nr-agent-system:latest

# Docker Desktop K8s
# 无需额外操作，镜像已可用
```

### 第四步：部署到 K8s

```bash
# 方式一：使用部署脚本（推荐）
chmod +x deploy.sh
./deploy.sh

# 方式二：手动部署
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/pvc.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/hpa.yaml
```

### 第五步：验证部署

```bash
# 查看 Pod 状态
kubectl get pods -n 5g-nr-agents

# 查看服务状态
kubectl get svc -n 5g-nr-agents

# 查看部署状态
kubectl get deployment -n 5g-nr-agents

# 查看 HPA 状态
kubectl get hpa -n 5g-nr-agents
```

---

## 运行与验证

### 检查 Pod 就绪状态

```bash
# 等待所有 Pod 就绪
kubectl wait --for=condition=ready pod -l app=5g-nr-agent -n 5g-nr-agents --timeout=300s
```

### 端口转发（本地访问）

```bash
# 将本地 8000 端口转发到服务
kubectl port-forward svc/5g-nr-agent-service 8000:80 -n 5g-nr-agents
```

### 测试健康检查

```bash
# 新终端执行
curl http://localhost:8000/health
```

### 查看应用日志

```bash
# 查看所有 Pod 日志
kubectl logs -n 5g-nr-agents -l app=5g-nr-agent

# 查看特定 Pod 日志
kubectl logs -n 5g-nr-agents <pod-name>

# 实时跟踪日志
kubectl logs -f -n 5g-nr-agents -l app=5g-nr-agent
```

---

## 日常运维

### 查看资源状态

```bash
# 查看所有资源
kubectl get all -n 5g-nr-agents

# 查看 Pod 详情
kubectl describe pod -n 5g-nr-agents -l app=5g-nr-agent

# 查看资源使用情况
kubectl top pods -n 5g-nr-agents
kubectl top nodes
```

### 扩缩容

```bash
# 手动扩缩容
kubectl scale deployment 5g-nr-agent-system -n 5g-nr-agents --replicas=5

# 查看 HPA 状态
kubectl get hpa -n 5g-nr-agents
```

### 滚动更新

```bash
# 更新镜像
kubectl set image deployment/5g-nr-agent-system \
  agent-system=5g-nr-agent-system:v2.0 \
  -n 5g-nr-agents

# 查看更新状态
kubectl rollout status deployment/5g-nr-agent-system -n 5g-nr-agents

# 查看更新历史
kubectl rollout history deployment/5g-nr-agent-system -n 5g-nr-agents

# 回滚到上一版本
kubectl rollout undo deployment/5g-nr-agent-system -n 5g-nr-agents

# 回滚到指定版本
kubectl rollout undo deployment/5g-nr-agent-system -n 5g-nr-agents --to-revision=2
```

### 更新配置

```bash
# 更新 ConfigMap
kubectl edit configmap 5g-nr-config -n 5g-nr-agents

# 重启 Pod 使配置生效
kubectl rollout restart deployment 5g-nr-agent-system -n 5g-nr-agents
```

### 进入 Pod 调试

```bash
# 进入 Pod 的 shell
kubectl exec -it -n 5g-nr-agents <pod-name> -- /bin/bash

# 执行命令
kubectl exec -n 5g-nr-agents <pod-name> -- python --version
```

---

## 监控与日志

### 内置健康检查

Deployment 配置了两种健康检查：

| 类型 | 间隔 | 超时 | 初始延迟 | 失败阈值 |
|------|------|------|---------|---------|
| Liveness | 30s | 10s | 60s | 3 |
| Readiness | 10s | 5s | 30s | 3 |

### 日志管理

```bash
# 查看最近 100 行日志
kubectl logs -n 5g-nr-agents -l app=5g-nr-agent --tail=100

# 查看最近 1 小时日志
kubectl logs -n 5g-nr-agents -l app=5g-nr-agent --since=1h

# 导出日志到文件
kubectl logs -n 5g-nr-agents -l app=5g-nr-agent > logs.txt
```

### 事件监控

```bash
# 查看命名空间事件
kubectl get events -n 5g-nr-agents --sort-by='.lastTimestamp'

# 持续监控事件
kubectl get events -n 5g-nr-agents --watch
```

---

## 故障排查

### Pod 无法启动

```bash
# 查看 Pod 状态
kubectl describe pod -n 5g-nr-agents <pod-name>

# 常见问题：
# 1. ImagePullBackOff - 镜像拉取失败
# 2. CrashLoopBackOff - 容器启动后崩溃
# 3. Pending - 资源不足或调度问题
```

### 镜像拉取失败

```bash
# 检查镜像是否存在
docker images | grep 5g-nr-agent-system

# 本地 K8s 需要加载镜像
minikube image load 5g-nr-agent-system:latest
```

### 资源不足

```bash
# 查看节点资源
kubectl describe nodes

# 查看资源配额
kubectl get resourcequota -n 5g-nr-agents
```

### 服务无法访问

```bash
# 检查 Service
kubectl get svc -n 5g-nr-agents
kubectl describe svc 5g-nr-agent-service -n 5g-nr-agents

# 检查 Endpoints
kubectl get endpoints -n 5g-nr-agents

# 测试服务连通性
kubectl run -it --rm debug --image=busybox --restart=Never -- wget -qO- http://5g-nr-agent-service:80
```

### 数据库持久化问题

```bash
# 检查 PVC 状态
kubectl get pvc -n 5g-nr-agents
kubectl describe pvc 5g-nr-data-pvc -n 5g-nr-agents

# 检查 PV 绑定
kubectl get pv
```

---

## 常见问题

### Q1: 如何修改 API Key？

```bash
# 编辑 Secret
kubectl edit secret 5g-nr-secret -n 5g-nr-agents

# 或重新应用
kubectl apply -f k8s/secret.yaml

# 重启 Pod 使配置生效
kubectl rollout restart deployment 5g-nr-agent-system -n 5g-nr-agents
```

### Q2: 如何更新知识库？

```bash
# 方式一：重建镜像（推荐）
# 1. 更新 data/5g_knowledge.md
# 2. 重新构建镜像
docker build -t 5g-nr-agent-system:v2 .
# 3. 更新部署
kubectl set image deployment/5g-nr-agent-system agent-system=5g-nr-agent-system:v2 -n 5g-nr-agents

# 方式二：使用 ConfigMap 挂载
kubectl create configmap knowledge-base --from-file=data/5g_knowledge.md -n 5g-nr-agents
```

### Q3: 如何调整资源限制？

编辑 `k8s/deployment.yaml` 中的 resources 部分：

```yaml
resources:
  requests:
    memory: "4Gi"  # 增加内存请求
    cpu: "2000m"   # 增加 CPU 请求
  limits:
    memory: "8Gi"  # 增加内存限制
    cpu: "4000m"   # 增加 CPU 限制
```

然后重新应用：

```bash
kubectl apply -f k8s/deployment.yaml
```

### Q4: 如何启用外部访问？

1. 安装 Ingress Controller（如 Nginx）
2. 配置 DNS 指向集群
3. 创建 TLS Secret
4. 应用 Ingress 配置

```bash
# 创建 TLS Secret
kubectl create secret tls 5g-nr-tls-secret \
  --cert=path/to/tls.crt \
  --key=path/to/tls.key \
  -n 5g-nr-agents

# 应用 Ingress
kubectl apply -f k8s/ingress.yaml
```

### Q5: 如何备份数据？

```bash
# 备份 PVC 数据
kubectl run backup -n 5g-nr-agents --image=busybox --restart=Never \
  --command -- tar czf /tmp/backup.tar.gz /app/data

# 拷贝到本地
kubectl cp 5g-nr-agents/backup:/tmp/backup.tar.gz ./backup.tar.gz
```

### Q6: 如何完全卸载？

```bash
# 删除所有资源
kubectl delete namespace 5g-nr-agents

# 或逐个删除
kubectl delete -f k8s/hpa.yaml
kubectl delete -f k8s/ingress.yaml
kubectl delete -f k8s/service.yaml
kubectl delete -f k8s/deployment.yaml
kubectl delete -f k8s/pvc.yaml
kubectl delete -f k8s/secret.yaml
kubectl delete -f k8s/configmap.yaml
kubectl delete -f k8s/namespace.yaml
```

---

## 附录

### 完整部署命令清单

```bash
# 1. 构建镜像
docker build -t 5g-nr-agent-system:latest .

# 2. 加载镜像（本地 K8s）
minikube image load 5g-nr-agent-system:latest

# 3. 部署
kubectl apply -f k8s/

# 4. 验证
kubectl get pods -n 5g-nr-agents
kubectl get svc -n 5g-nr-agents

# 5. 端口转发
kubectl port-forward svc/5g-nr-agent-service 8000:80 -n 5g-nr-agents
```

### 环境变量参考

| 变量名 | 必填 | 说明 |
|--------|------|------|
| DEEPSEEK_API_KEY | 是 | DeepSeek API 密钥 |
| MODEL_NAME | 否 | 模型名称，默认 deepseek-chat |
| KNOWLEDGE_BASE | 否 | 知识库路径 |
| PERSIST_DIR | 否 | 向量数据库路径 |
| LOG_LEVEL | 否 | 日志级别，默认 INFO |

### 相关文档

- [架构设计文档](ARCHITECTURE_DESIGN.md)
- [面试指南](INTERVIEW_GUIDE.md)
- [测试说明](tests/test_info.md)
