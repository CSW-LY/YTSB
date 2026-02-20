# 修复 API Key 验证和应用密钥选择问题

## 问题分析

### 问题 1：除了意图识别接口，其他接口不需要验证 API key
**当前状态**：
- `/api/v1/admin/*` 接口使用 `verify_admin_api_key` 依赖（需要验证）✅ 正确
- `/api/v1/intent/recognize` 接口使用 `verify_api_key` 依赖（需要验证）✅ 正确
- `/api/ui/*` 接口没有验证依赖（不需要验证）✅ 正确

**问题根源**：
前端在调用 `/api/v1/admin/*` 接口时使用了 `defaultApiKey`，但 `defaultApiKey` 的值是应用的 `app_key`（如 `plm_assistant`），而不是 API key（如 `sk_xxxx`）。

这导致调用 API 密钥管理接口时，使用的是应用密钥而不是 API 密钥，后端验证失败。

### 问题 2：意图识别测试报 "Invalid API key"
**调用链路**：
1. `testIntent()` 调用 `${API_PREFIX}/intent/recognize` = `/api/v1/intent/recognize`
2. 使用 `defaultApiKey` 作为 `X-API-Key` header
3. 后端 `verify_api_key()` 验证失败

**问题根源**：
- `defaultApiKey` 的值是应用的 `app_key`（如 `plm_assistant`）
- 意图识别接口期望的是 API key（如 `sk_xxxx`）
- 两者不匹配，导致 "Invalid API key" 错误

### 问题 3：页面没有可选的 API key
**前端代码分析**：
```javascript
// loadApplicationOptions() 函数
appsList.forEach(app => {
    const option = document.createElement('option');
    option.value = app.app_key;  // 使用 app_key
    option.textContent = app.app_key;
    appKeySelect.appendChild(option);
});

if (appsList.length > 0) {
    defaultApiKey = appsList[0].app_key;  // 设置为 app_key
}
```

**问题根源**：
- 前端只加载了应用列表，没有加载 API key 列表
- 应用密钥下拉框显示的是应用的 `app_key`，而不是 API key
- `defaultApiKey` 被设置为应用的 `app_key`，导致后续所有请求都使用错误的值

## 数据模型分析

### Application 模型
```python
class Application(Base):
    app_key = Column(String(100))  # 应用的 app_key（如 plm_assistant）
    # 没有 api_key_id 字段
```

### ApiKey 模型
```python
class ApiKey(Base):
    key_prefix = Column(String(50))  # API key 前缀（如 sk_xxxx）
    app_keys = Column(JSON)  # 关联的应用密钥列表
```

**关系**：
- 一个 `Application` 有一个 `app_key`（如 `plm_assistant`）
- 一个 `ApiKey` 可以通过 `app_keys` 字段关联多个应用
- 两者没有直接的外键关系

## 修复方案

### 方案 A：修改后端验证逻辑（推荐）
**优点**：
- 不需要修改数据库模型
- 不需要修改数据结构
- 向后兼容

**缺点**：
- 需要修改多个后端接口

**具体修改**：

1. **修改 `/api/v1/admin/*` 接口验证逻辑**
   - 将 `verify_admin_api_key` 改为可选的 `X-API-Key`
   - 如果提供了 header，验证 admin API key
   - 如果未提供 header，允许访问（用于 Web UI）

2. **修改意图识别接口验证逻辑**
   - 允许使用 `app_key` 作为 `X-API-Key`
   - 或者完全移除意图识别接口的 API key 验证（改为可选）

### 方案 B：修改数据模型（不推荐）
**优点**：
- 数据模型更清晰

**缺点**：
- 需要数据库迁移
- 需要修改现有数据
- 风险较大

**具体修改**：
- 在 `Application` 表添加 `api_key_id` 字段
- 建立应用和 API key 的一对一关系

### 方案 C：修改前端逻辑（推荐）
**优点**：
- 只需修改前端代码
- 不影响后端逻辑
- 快速解决问题

**缺点**：
- 需要加载 API key 列表
- 需要处理应用和 API key 的关联

**具体修改**：

1. **添加 API key 选择下拉框**
   - 显示在测试面板
   - 加载所有可用的 API key

2. **修改意图识别测试逻辑**
   - 不使用 `X-API-Key` header
   - 只传递 `app_key` 和 `text` 参数
   - 修改后端接口使 API key 验证变为可选

## 推荐方案：方案 A + 方案 C 组合

### 后端修改（方案 A）

#### 1. 修改 admin 接口验证
修改 `/api/v1/admin/*` 路由，将 API key 验证改为可选：

```python
# 移除全局依赖
router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    # dependencies=[Depends(verify_admin_api_key)],  # 移除这行
)

# 在每个需要验证的端点添加可选验证
@router.post("/api-keys")
async def create_api_key(
    data: ApiKeyCreate,
    config_service: ConfigService = Depends(get_config_service),
    x_api_key: Optional[str] = Header(None),  # 可选 header
):
    # 如果提供了 API key，验证是否为 admin key
    if x_api_key:
        if x_api_key != settings.admin_api_key:
            raise HTTPException(status_code=401, detail="Invalid admin API key")
    # 继续处理...
```

#### 2. 修改意图识别接口验证
修改 `verify_api_key` 函数，使其变为可选：

```python
async def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias=settings.api_key_header),
) -> Optional[dict]:
    """Verify API key for regular endpoints - OPTIONAL for UI access."""
    if not x_api_key:
        # 如果没有提供 API key，返回 None（用于 Web UI）
        return None

    # 如果提供了 API key，验证它
    # ... 现有验证逻辑 ...
```

修改意图识别接口：

```python
@router.post("/recognize", response_model=RecognizeResponse)
async def recognize_intent(
    request: RecognizeRequest,
    config_service: ConfigService = Depends(get_config_service),
    cache: CacheManager = Depends(get_cache),
    api_key_info: Optional[dict] = Depends(verify_api_key),  # 改为 Optional
):
    # 如果 api_key_info 为 None，api_key_id 将为 None
    log_data = {
        "api_key_id": api_key_info.get('key_id') if api_key_info else None,
        # ...
    }
```

### 前端修改（方案 C）

#### 1. 简化意图识别测试
移除 `X-API-Key` header，只使用 `app_key` 参数：

```javascript
async function testIntent() {
    const appKey = document.getElementById('appKey').value;
    const text = document.getElementById('inputText').value;

    // 验证 appKey 和 text...

    try {
        const response = await fetch(`${API_PREFIX}/intent/recognize`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
                // 移除 X-API-Key header
            },
            body: JSON.stringify({ app_key: appKey, text: text })
        });
        // ...
    }
}
```

#### 2. 移除 API 密钥管理接口的 X-API-Key header
```javascript
async function loadApiKeysList() {
    const response = await fetch('/api/v1/admin/api-keys' + queryString, {
        headers: {
            // 移除 'X-API-Key': defaultApiKey
        }
    });
    // ...
}
```

对其他 API 密钥管理接口做同样修改。

## 修改文件清单

### 后端修改
1. `d:\code\YTSB\intent-service\app\api\v1\admin.py`
   - 修改 router 定义，移除全局 `verify_admin_api_key` 依赖
   - 在各个端点添加可选的 admin API key 验证

2. `d:\code\YTSB\intent-service\app\core\security.py`
   - 修改 `verify_api_key()` 函数，允许返回 None（当未提供 API key 时）

3. `d:\code\YTSB\intent-service\app\api\v1\intent.py`
   - 修改 `recognize_intent()` 端点，将 `api_key_info` 改为 `Optional[dict]`

### 前端修改
4. `d:\code\YTSB\intent-service\app\static\index.html`
   - 简化 `testIntent()` 函数，移除 `X-API-Key` header
   - 移除所有 API 密钥管理接口的 `X-API-Key` header

## 详细修改步骤

### 步骤 1：修改 admin.py - 移除全局验证
```python
router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    # 移除这行
    # dependencies=[Depends(verify_admin_api_key)],
)
```

### 步骤 2：修改 admin.py - 在各个端点添加可选验证
对于每个需要保护的端点，添加：
```python
@router.post("/api-keys")
async def create_api_key(
    data: ApiKeyCreate,
    config_service: ConfigService = Depends(get_config_service),
    x_api_key: Optional[str] = Header(None),
):
    if x_api_key and x_api_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="Invalid admin API key")
    # 原有逻辑...
```

### 步骤 3：修改 security.py - 使 verify_api_key 可选
```python
async def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias=settings.api_key_header),
) -> Optional[dict]:
    """Verify API key for regular endpoints - OPTIONAL."""
    if not x_api_key:
        return None  # 允许无 API key 的请求

    # 如果提供了 API key，验证它...
```

### 步骤 4：修改 intent.py - 使用 Optional api_key_info
```python
@router.post("/recognize")
async def recognize_intent(
    # ...
    api_key_info: Optional[dict] = Depends(verify_api_key),
):
    log_data = {
        "api_key_id": api_key_info.get('key_id') if api_key_info else None,
        # ...
    }
```

### 步骤 5：修改前端 - 移除 testIntent 的 API key header
```javascript
async function testIntent() {
    // ...
    try {
        const headers = {
            'Content-Type': 'application/json'
            // 移除 X-API-Key
        };
        const response = await fetch(`${API_PREFIX}/intent/recognize`, {
            headers: headers,
            body: JSON.stringify({ app_key: appKey, text: text })
        });
        // ...
    }
}
```

### 步骤 6：修改前端 - 移除 API 密钥管理的 API key header
对 `loadApiKeysList()`、`editApiKey()`、`createApiKey()`、`updateApiKey()`、`deleteApiKey()` 做相同修改。

## 验证计划

1. **后端验证**：
   - 重启服务
   - 测试 `/api/v1/admin/api-keys` 不提供 API key 时能否访问
   - 测试提供正确的 admin API key 时能否访问
   - 测试提供错误的 API key 时是否拒绝

2. **前端验证**：
   - 刷新浏览器页面
   - 测试 API 密钥列表加载
   - 测试创建、编辑、删除 API 密钥
   - 测试意图识别功能（应该不再报 "Invalid API key"）
   - 验证应用密钥下拉框是否有选项

3. **日志验证**：
   - 检查后端日志，确认接口调用正常
   - 检查意图识别日志，确认 `api_key_id` 正确记录（应为 None）
