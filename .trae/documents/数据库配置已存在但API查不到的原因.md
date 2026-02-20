# 数据库配置已存在但 API 查不到的原因

## 问题

数据库中已有 `plm_assistant` 应用配置，但 API Debug Platform 提示：`App configuration not found: plm_assistant`

## 可能原因分析

### 1. 数据库连接不一致

**问题描述**：
- `main.py` 和 `main_ui.py` 各自创建 `async_session_maker` 实例
- 两个实例连接到同一个数据库 URL，但是不同的连接池
- 在不同连接池中的数据可能不立即可见

**相关代码**：
- `app/main.py:31-35`：创建 `async_session_maker`
- `app/main_ui.py:391`：创建 `async_session_maker`
- `app/api/v1/admin.py:42`：从 `app.main` 导入（错误）
- `app/api/v1/intent.py:51`：从 `app/main_ui` 导入（正确）

### 2. Admin API 使用错误的会话工厂

**问题描述**：
- `app/api/v1/admin.py:42` 中的 `get_config_service` 从 `app.main` 导入 `async_session_maker`
- 但当前运行环境是 `main_ui.py`，应该从 `app/main_ui` 导入
- 如果通过 Admin API 创建配置，使用的是 `app.main` 的连接
- 如果通过 Web UI 创建配置，使用的是 `main_ui.py` 的连接

### 3. 缓存干扰

**问题描述**：
- `ConfigService` 使用 `LRUCache` 缓存应用配置
- 缓存键是 `app_key`，而不是 `context:{app_key}`
- 如果两个会话工厂的缓存不同步，可能导致问题

## 解决方案

### 方案 1：统一数据库连接（推荐）

**步骤 1**：修复 Admin API 的导入
```python
# app/api/v1/admin.py:42
# 之前
from app.main import async_session_maker

# 修改为
from app.main_ui import async_session_maker
```

**步骤 2**：共享 `async_session_maker` 实例

将 `async_session_maker` 移到共享模块：
```python
# app/core/database.py

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.async_database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    echo=settings.debug,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
```

然后在 `main.py` 和 `main_ui.py` 中导入：
```python
from app.core.database import async_session_maker
```

### 方案 2：直接通过 Admin API 创建配置

使用 `admin_sk_1234567890abcdef` API Key 创建配置：

```bash
curl -X POST http://localhost:8000/api/v1/admin/apps/plm_assistant/intents \
  -H "Content-Type: application/json" \
  -H "X-API-Key: admin_sk_1234567890abcdef" \
  -d '{
    "intent_ids": [1, 2, 3],
    "confidence_threshold": 0.7,
    "enable_cache": true
  }'
```

### 方案 3：验证配置

检查数据库中实际存在的配置：

```bash
# 连接到数据库
psql -h localhost -p 5432 -U postgres -d intent_service

# 查询应用配置
SELECT app_key, intent_ids, confidence_threshold, enable_cache, created_at
FROM app_intents
WHERE app_key = 'plm_assistant';
```

## 推荐步骤

1. 先修复 `admin.py` 的导入问题（方案 1 步骤 1）
2. 重启服务
3. 如果问题仍存在，使用 Admin API 创建配置（方案 2）
4. 验证配置是否正确创建
