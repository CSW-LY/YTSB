# 启动状态日志增强 - 产品需求文档

## 概述
- **Summary**: 为 intent-service 项目添加更详细的启动状态日志，以便 AI 能够实时监控启动过程，避免因启动时间长而误判为启动失败。
- **Purpose**: 解决当前启动过程中日志信息不足，导致 AI 无法准确判断启动状态的问题。
- **Target Users**: 开发人员、运维人员以及 AI 助手。

## Goals
- 提供清晰的启动阶段划分和状态日志
- 增加时间戳和阶段耗时信息
- 确保关键步骤都有明确的开始和完成日志
- 提供启动状态的可查询接口
- 保持日志输出的可读性和一致性

## Non-Goals (Out of Scope)
- 重构现有的启动流程逻辑
- 修改核心功能代码
- 增加新的依赖库
- 改变现有的配置方式

## Background & Context
- 项目启动时间约为 5 分钟，主要耗时在模型加载和初始化过程
- 当前启动日志不够详细，无法清晰反映启动进度
- AI 助手可能会因为长时间无输出而误判启动失败
- 项目使用 uvicorn 作为 ASGI 服务器，FastAPI 作为框架

## Functional Requirements
- **FR-1**: 在 start_with_ui.py 中添加详细的启动阶段日志
- **FR-2**: 在 main_ui.py 的 lifespan 函数中增加更详细的初始化步骤日志
- **FR-3**: 为关键操作添加时间戳和耗时统计
- **FR-4**: 提供启动状态的 API 接口，方便外部查询
- **FR-5**: 确保日志输出格式一致，便于 AI 解析

## Non-Functional Requirements
- **NFR-1**: 日志级别设置合理，关键信息使用 INFO 级别
- **NFR-2**: 日志输出清晰易读，包含足够的上下文信息
- **NFR-3**: 不影响项目的正常启动时间和性能
- **NFR-4**: 保持代码的可维护性和可读性

## Constraints
- **Technical**: 基于现有的 Python 日志系统，不引入新的日志库
- **Business**: 保持现有启动流程不变，仅增强日志输出
- **Dependencies**: 依赖现有的 logging 模块和 FastAPI 框架

## Assumptions
- 项目使用 Python 标准库的 logging 模块进行日志记录
- 启动过程中的主要耗时操作包括模型加载、数据库连接、缓存初始化等
- 现有的启动流程逻辑正确，无需修改

## Acceptance Criteria

### AC-1: 启动阶段日志增强
- **Given**: 启动 intent-service 项目
- **When**: 执行 start_with_ui.py 脚本
- **Then**: 控制台输出包含清晰的启动阶段划分，每个阶段都有开始和完成日志
- **Verification**: `human-judgment`
- **Notes**: 日志应包含模型加载、应用创建、服务器启动等关键阶段

### AC-2: 时间戳和耗时信息
- **Given**: 启动 intent-service 项目
- **When**: 执行 start_with_ui.py 脚本
- **Then**: 每个关键操作都有时间戳和耗时统计信息
- **Verification**: `programmatic`
- **Notes**: 耗时统计应精确到毫秒

### AC-3: 启动状态 API 接口
- **Given**: 项目启动中
- **When**: 访问 /api/ui/startup/status 接口
- **Then**: 返回当前启动状态和进度信息
- **Verification**: `programmatic`
- **Notes**: 接口应返回启动阶段、状态、耗时等信息

### AC-4: 日志格式一致性
- **Given**: 启动 intent-service 项目
- **When**: 查看启动日志
- **Then**: 日志格式一致，包含时间戳、日志级别、模块名和消息内容
- **Verification**: `human-judgment`
- **Notes**: 日志格式应便于 AI 解析和理解

### AC-5: 关键步骤详细日志
- **Given**: 项目启动过程中
- **When**: 执行到模型加载、数据库连接等关键步骤
- **Then**: 输出详细的日志信息，包括步骤开始、执行中、完成状态
- **Verification**: `human-judgment`
- **Notes**: 对于可能耗时较长的操作，应提供进度提示

## Open Questions
- [ ] 是否需要在启动过程中添加更多的健康检查点？
- [ ] 启动状态 API 接口是否需要添加认证机制？
- [ ] 是否需要将启动日志保存到文件中以便后续分析？