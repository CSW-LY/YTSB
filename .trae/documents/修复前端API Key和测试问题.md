# 修复前端 API Key 和测试问题

## 问题分析

### 问题 1：加载 API KEY 列表失败
**原因**：前端代码中仍有 5 处使用已删除的 `ADMIN_API_KEY` 变量，导致 API 请求失败。

**受影响的函数**：
1. `loadApiKeysList()` - 加载 API 密钥列表（第 2287 行）
2. `editApiKey()` - 获取 API 密钥详情（第 2038 行）
3. `createApiKey()` - 创建新 API 密钥（第 2090 行）
4. `updateApiKey()` - 更新 API 密钥（第 2137 行）
5. `deleteApiKey()` - 删除 API 密钥（第 2425 行）

**错误示例**：
```javascript
const response = await fetch('/api/v1/admin/api-keys' + queryString, {
    headers: {
        'X-API-Key': ADMIN_API_KEY  // ❌ ADMIN_API_KEY 未定义
    }
});
```

### 问题 2：点击测试按钮意图识别接口没调用
**原因**：`testIntent()` 函数中使用了错误的 DOM 元素 ID。

**问题代码**（第 888 行）：
```javascript
const apiKey = document.getElementById('apiKey').value || defaultApiKey;
```

**HTML 结构**（第 272 行）：
```html
<div class="form-group hidden"><label>API密钥</label><select id="testApiKey"><option value="">请选择API密钥</option></select></div>
```

**分析**：
- JavaScript 代码尝试获取 `id="apiKey"` 的元素
- 但 HTML 中的实际 ID 是 `id="testApiKey"`
- 该元素还被设置为 `class="hidden"`，默认是隐藏的
- 这导致 `document.getElementById('apiKey')` 返回 `null`，获取不到 API key

## 修复方案

### 修复 1：替换所有 ADMIN_API_KEY 引用
将所有使用 `ADMIN_API_KEY` 的地方改为使用用户选择的 API key。

**修改策略**：
- 对于 API 密钥管理功能，使用专门的 API 密钥选择框（`#testApiKey` 或新增 `#adminApiKey`）
- 保持与 `testIntent()` 相同的逻辑：优先使用用户选择的，否则使用默认的

### 修复 2：修正 testIntent() 中的 DOM 元素 ID
**方案 A**（推荐）：完全移除 API key 检查，直接使用 `defaultApiKey`
- 意图识别不需要 API key，只需要 `app_key`
- 简化逻辑，避免混淆

**方案 B**：修正元素 ID 为 `testApiKey`
- 修改第 888 行：`const apiKey = document.getElementById('testApiKey').value || defaultApiKey;`
- 但需要考虑该元素是隐藏的

**推荐采用方案 A**，因为：
1. 意图识别接口（`/api/v1/intent/recognize`）只需要 `app_key` 参数
2. `X-API-Key` header 是可选的，用于记录日志
3. 使用 `defaultApiKey` 可以确保日志正确记录

## 修改文件清单

1. `d:\code\YTSB\intent-service\app\static\index.html`
   - 修复 `loadApiKeysList()` - 第 2287 行
   - 修复 `editApiKey()` - 第 2038 行
   - 修复 `createApiKey()` - 第 2090 行
   - 修复 `updateApiKey()` - 第 2137 行
   - 修复 `deleteApiKey()` - 第 2425 行
   - 简化 `testIntent()` - 第 888 行

## 详细修改步骤

### 步骤 1：修复 loadApiKeysList() 函数
将 `ADMIN_API_KEY` 改为使用默认 API key

```javascript
const response = await fetch('/api/v1/admin/api-keys' + queryString, {
    headers: {
        'X-API-Key': defaultApiKey
    }
});
```

### 步骤 2：修复 editApiKey() 函数
```javascript
const response = await fetch(url, {
    headers: {
        'X-API-Key': defaultApiKey
    }
});
```

### 步骤 3：修复 createApiKey() 函数
```javascript
const response = await fetch('/api/v1/admin/api-keys', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-API-Key': defaultApiKey
    },
    body: JSON.stringify({ ... })
});
```

### 步骤 4：修复 updateApiKey() 函数
```javascript
const response = await fetch(`/api/v1/admin/api-keys/${id}`, {
    method: 'PUT',
    headers: {
        'Content-Type': 'application/json',
        'X-API-Key': defaultApiKey
    },
    body: JSON.stringify({ ... })
});
```

### 步骤 5：修复 deleteApiKey() 函数
```javascript
const response = await fetch(`/api/v1/admin/api-keys/${apiKey}`, {
    method: 'DELETE',
    headers: {
        'X-API-Key': defaultApiKey
    }
});
```

### 步骤 6：简化 testIntent() 函数
移除对 `#apiKey` 元素的查找，直接使用 `defaultApiKey`

```javascript
// 移除这行
// const apiKey = document.getElementById('apiKey').value || defaultApiKey;

// 简化为
const apiKey = defaultApiKey;

// 或者更简单，直接在请求头中添加
const headers = { 'Content-Type': 'application/json' };
if (defaultApiKey) {
    headers['X-API-Key'] = defaultApiKey;
}
```

## 验证计划

1. 刷新浏览器页面
2. 测试 API 密钥管理功能：
   - 加载 API 密钥列表
   - 创建新 API 密钥
   - 编辑 API 密钥
   - 删除 API 密钥
3. 测试意图识别功能：
   - 选择应用密钥
   - 输入测试文本
   - 点击"识别意图"按钮
   - 验证接口是否被调用
   - 验证返回结果
4. 检查浏览器控制台是否还有错误
5. 检查后端日志，确认 API key 记录正确
