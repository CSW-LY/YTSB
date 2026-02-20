# Intent Recognition Service

一个面向 PLM 场景的高性能意图识别服务，支持可配置、可扩展、高性能、高可用。

## 特性

- **多策略识别链**：关键词 → 正则 → 语义 → LLM，兼顾速度与准确性
- **高性能**：基于 FastAPI 异步框架，目标 QPS > 1000，RT < 200ms
- **可配置**：数据库动态配置，支持热更新
- **可扩展**：插件化设计，支持自定义识别策略
- **高可用**：无状态设计，支持水平扩展，支持 Kubernetes 部署
- **缓存优化**：Redis 缓存常见输入，命中时 RT < 10ms

## 技术栈

| 组件 | 技术 |
|------|------|
| 框架 | FastAPI |
| 数据库 | PostgreSQL |
| 缓存 | Redis |
| 嵌入模型 | BGE-M3 / BGE-Large-ZH |
| 推理引擎 | vLLM (可选) |
| 部署 | Docker / Kubernetes |

## 快速开始

### 1. 环境要求

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- CUDA (可选，用于 GPU 加速)

### 2. 安装依赖

```bash
cd intent-service
pip install -r requirements.txt
```

### 3. 配置环境

复制 `.env.example` 到 `.env` 并修改配置：

```bash
cp .env.example .env
```

### 4. 初始化数据库

```bash
# 创建表结构
python scripts/init_db.py init

# 插入示例数据
python scripts/init_db.py seed

# 或完整设置
python scripts/init_db.py setup
```

### 5. 启动服务

```bash
# 开发环境
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 生产环境
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

### 6. 访问 API 文档

启动后访问 `http://localhost:8000/docs` 查看交互式 API 文档。

## Docker 部署

### 使用 Docker Compose

```bash
# 构建镜像
docker-compose build

# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f intent-api
```

### 单独构建 Docker 镜像

```bash
docker build -t intent-service:latest .
docker run -d -p 8000:8000 --env-file .env intent-service:latest
```

## Kubernetes 部署

```bash
# 创建命名空间和部署
kubectl apply -f k8s/deployment.yaml

# 配置 Ingress
kubectl apply -f k8s/ingress.yaml

# 查看部署状态
kubectl get pods -n intent-service
kubectl get svc -n intent-service
```

## API 使用示例

### 意图识别

```bash
curl -X POST http://localhost:8000/api/v1/intent/recognize \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "app_key": "plm_assistant",
    "text": "帮我查询BOM结构中的物料信息",
    "context": {
      "user_id": "user123"
    }
  }'
```

响应：

```json
{
  "intent": "bom.query",
  "confidence": 0.92,
  "entities": {},
  "matched_rules": [
    {
      "id": 1,
      "rule_type": "keyword",
      "content": "bom结构",
      "weight": 0.9
    }
  ],
  "cached": false,
  "processing_time_ms": 15.3
}
```

### 批量识别

```bash
curl -X POST http://localhost:8000/api/v1/intent/recognize/batch \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "app_key": "plm_assistant",
    "texts": ["查询BOM结构", "创建新零件", "查看图纸"]
  }'
```

## 配置说明

### 意图分类

通过管理 API 创建意图分类：

```bash
curl -X POST http://localhost:8000/api/v1/admin/intents \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-admin-api-key" \
  -d '{
    "code": "custom.intent",
    "name": "自定义意图",
    "description": "这是一个自定义意图",
    "priority": 100
  }'
```

### 添加识别规则

支持三种类型的规则：

1. **关键词规则** (keyword)：精确或模糊关键词匹配
2. **正则规则** (regex)：正则表达式匹配，支持命名组提取实体
3. **语义规则** (semantic)：语义向量相似度匹配

```bash
curl -X POST http://localhost:8000/api/v1/admin/rules \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-admin-api-key" \
  -d '{
    "category_id": 1,
    "rule_type": "keyword",
    "content": "查询BOM",
    "weight": 1.0
  }'
```

## 性能优化

### 1. 模型量化

使用 INT8/INT4 量化可提升推理速度 2-4 倍。

### 2. 启用缓存

Redis 缓存可显著降低常见查询的延迟。

### 3. 批量处理

使用 `/api/v1/intent/recognize/batch` 接口处理多个请求。

### 4. 水平扩展

无状态设计支持多实例部署，建议使用 Kubernetes HPA 自动扩缩容。

## 监控

服务内置 Prometheus 指标，访问 `/metrics` 端点获取：

- `intent_recognition_duration_seconds`：识别耗时
- `intent_recognition_cache_hits_total`：缓存命中数
- `intent_recognition_requests_total`：请求总数

## 许可证

MIT License
