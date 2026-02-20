# 测试文件说明

本文件夹包含意图识别服务的测试文件。

## 测试文件列表

### test_api.py
意图识别API功能测试文件。用于测试意图识别的核心功能，包括关键词匹配、正则表达式匹配和语义匹配。

**主要测试内容：**
- 意图识别API接口
- 关键词匹配功能
- 正则表达式匹配功能
- 语义匹配功能
- API响应格式验证

**使用方法：**
```bash
python tests/test_api.py
```

### test_db_connection.py
数据库连接测试文件。用于测试与数据库的连接是否正常。

**主要测试内容：**
- 数据库连接配置
- 数据库连接建立
- 基本数据库操作

**使用方法：**
```bash
python tests/test_db_connection.py
```

### test_postgres_connection.py
PostgreSQL数据库连接测试文件。专门用于测试PostgreSQL数据库的连接。

**主要测试内容：**
- PostgreSQL连接配置
- PostgreSQL连接建立
- PostgreSQL特定功能测试

**使用方法：**
```bash
python tests/test_postgres_connection.py
```

### test_ui_api.py
UI API测试文件。用于测试前端界面调用的API接口。

**主要测试内容：**
- UI API接口
- 数据格式转换
- 分页功能
- 过滤功能

**使用方法：**
```bash
python tests/test_ui_api.py
```

### test_keyword_match.py
关键词匹配逻辑测试文件。专门用于测试关键词匹配的核心逻辑。

**主要测试内容：**
- 关键词匹配算法
- 多关键词匹配
- 优先级处理
- 性能测试

**使用方法：**
```bash
python tests/test_keyword_match.py
```

## 运行所有测试

要运行所有测试，可以使用以下命令：

```bash
# 运行单个测试
python tests/test_api.py

# 或者在项目根目录运行
cd intent-service
python tests/test_api.py
```

## 测试环境要求

- Python 3.8+
- PostgreSQL 数据库
- 相关依赖包（见 requirements.txt）

## 注意事项

1. 运行测试前，请确保数据库服务已启动
2. 运行测试前，请确保环境变量配置正确（见 .env.example）
3. 某些测试可能需要特定的测试数据
4. 测试过程中可能会创建测试数据，请勿在生产环境运行

## 添加新测试

添加新测试时，请遵循以下命名规范：
- 文件名格式：`test_<功能名称>.py`
- 测试函数命名：使用描述性的函数名
- 在本README中添加测试说明

## 测试数据清理

测试过程中创建的数据可以在测试后手动清理，或者在测试脚本中添加清理逻辑。
