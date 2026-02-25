# 性能优化计划

## 问题分析

### 现象
- 接口响应时间：4137ms
- 关键字匹配时间：7.12ms
- 识别链路时间：0.01ms
- 性能差异：关键字匹配比总响应快约580倍

### 性能瓶颈分析

#### 1. 缓存问题
- **Redis连接失败**：导致缓存禁用，每次请求都需要数据库查询
- **缓存策略**：缺少内存缓存作为Redis的fallback
- **缓存键生成**：每次都需要计算MD5哈希

#### 2. 数据库查询
- **配置获取**：每次请求都需要多次数据库查询
- **连接池**：可能需要优化连接池配置
- **查询优化**：缺少索引和预编译语句

#### 3. 识别器链初始化
- **首次请求**：需要初始化识别器链
- **缓存机制**：识别器链缓存可能不够完善
- **模型加载**：虽然启动时预加载，但可能存在其他初始化开销

#### 4. 请求处理流程
- **API端点逻辑**：包含多个步骤，每个步骤都有开销
- **异常处理**：可能存在不必要的异常捕获
- **日志记录**：异步日志可能影响性能

## 优化方案

### 1. 缓存优化

#### 1.1 内存缓存作为Redis Fallback
```python
# 在CacheManager中添加内存缓存
class CacheManager:
    def __init__(self):
        self._pool: Optional[Redis] = None
        self._memory_cache: Dict[str, Tuple[Any, float]] = {}  # (value, expiry_timestamp)
        self._memory_cache_max_size = 1000
        self._memory_cache_ttl = 300

    async def get(self, key: str) -> Optional[Any]:
        if not settings.enable_cache:
            return None
        
        # 先尝试Redis
        if self._pool:
            try:
                value = await self._pool.get(self._get_key(key))
                if value:
                    return json.loads(value)
            except Exception as e:
                logger.warning(f"Cache get error: {e}")
        
        # Redis失败时尝试内存缓存
        memory_key = self._get_key(key)
        if memory_key in self._memory_cache:
            value, expiry = self._memory_cache[memory_key]
            if time.time() < expiry:
                return value
            # 过期项清理
            del self._memory_cache[memory_key]
        
        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        success = False
        ttl = ttl or settings.cache_ttl
        
        # 尝试Redis
        if self._pool:
            try:
                await self._pool.set(
                    self._get_key(key),
                    json.dumps(value),
                    ex=ttl,
                )
                success = True
            except Exception as e:
                logger.warning(f"Cache set error: {e}")
        
        # 同时更新内存缓存
        memory_key = self._get_key(key)
        expiry = time.time() + ttl
        self._memory_cache[memory_key] = (value, expiry)
        
        # 内存缓存大小控制
        if len(self._memory_cache) > self._memory_cache_max_size:
            # 移除最旧的项
            oldest_key = min(self._memory_cache.items(), key=lambda x: x[1][1])[0]
            del self._memory_cache[oldest_key]
        
        return success
```

#### 1.2 优化缓存键生成
```python
def generate_cache_key(app_key: str, text: str, context: Optional[dict] = None) -> str:
    """Generate cache key for intent recognition."""
    import hashlib
    
    # 简化缓存键生成
    content = f"{app_key}:{text[:100]}"  # 限制文本长度
    if context:
        # 只使用context的关键部分
        context_hash = hashlib.md5(json.dumps(context, sort_keys=True).encode()).hexdigest()[:8]
        content += f":{context_hash}"
    
    return hashlib.md5(content.encode()).hexdigest()
```

### 2. 数据库优化

#### 2.1 优化配置服务缓存
```python
class ConfigService:
    def __init__(self, db_session: AsyncSession):
        """Initialize config service."""
        self.db = db_session
        self.app_cache = LRUCache(max_size=100, ttl_seconds=600)  # 增加TTL
        self.context_cache = LRUCache(max_size=100, ttl_seconds=600)  # 增加TTL

    async def get_app_intent_context(
        self, 
        app_key: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get complete context for intent recognition with application binding.
        """
        context_key = f"context:{app_key}"
        cached = await self.context_cache.get(context_key)
        
        if cached is None:
            # 批量查询优化
            application = await self.get_application_by_key(app_key)
            if not application:
                return None
            
            app_config = await self.get_app_config(app_key)
            if not app_config:
                return None
            
            # 批量获取分类和规则
            categories = await self.get_categories_by_application(
                application.id,
                is_active=True
            )
            
            if categories:
                category_ids = [c.id for c in categories]
                rules = await self.get_active_rules(category_ids)
            else:
                rules = []
            
            context = {
                "application": application,
                "app_config": app_config,
                "categories": categories,
                "rules": rules,
            }
            
            await self.context_cache.set(context_key, context)
            return context
        
        return cached
```

### 3. 识别器链优化

#### 3.1 优化识别器链缓存
```python
async def get_recognizer_chain_for_app(app_config: AppIntent) -> RecognizerChain:
    """
    根据应用配置创建或获取缓存的识别器链。
    """
    config_key = _get_app_config_key(app_config)
    
    if config_key in _recognizer_chain_cache:
        logger.debug(f"Using cached recognizer chain for {app_config.app_key}")
        return _recognizer_chain_cache[config_key]
    
    logger.info(f"Creating new recognizer chain for {app_config.app_key}")
    recognizers = []
    
    # 优化识别器初始化顺序
    if app_config.enable_keyword_matching:
        recognizers.append(KeywordRecognizer())
    
    if app_config.enable_regex_matching:
        recognizers.append(RegexRecognizer())
    
    # 语义和LLM识别器初始化较耗时，放在后面
    if app_config.enable_semantic_matching and settings.enable_semantic_matching:
        try:
            semantic_recognizer = SemanticRecognizer({
                "threshold": settings.semantic_similarity_threshold,
            })
            await semantic_recognizer.initialize()
            recognizers.append(semantic_recognizer)
        except Exception as e:
            logger.warning(f"Failed to initialize semantic recognizer: {e}")
    
    if app_config.enable_llm_fallback and settings.enable_llm_fallback:
        try:
            llm_recognizer = LLMRecognizer()
            await llm_recognizer.initialize()
            recognizers.append(llm_recognizer)
        except Exception as e:
            logger.warning(f"Failed to initialize LLM recognizer: {e}")
    
    chain = RecognizerChain(recognizers)
    await chain.initialize_all()
    
    _recognizer_chain_cache[config_key] = chain
    _config_version_cache[config_key] = config_key
    
    logger.info(
        f"Cached recognizer chain for app {app_config.app_key} with {len(recognizers)} recognizers"
    )
    return chain
```

### 4. API端点优化

#### 4.1 优化请求处理逻辑
```python
@router.post("/recognize", response_model=RecognizeResponse)
async def recognize_intent(
    request: RecognizeRequest,
    config_service: ConfigService = Depends(get_config_service),
    cache: CacheManager = Depends(get_cache),
    api_key_info: Optional[dict] = Depends(verify_api_key),
):
    """
    识别用户输入的意图。
    """
    import time
    start_time = time.time()
    log_data = {
        "app_key": request.app_key,
        "api_key_id": api_key_info.get('key_id') if api_key_info else None,
        "input_text": request.text,
        "is_success": True,
        "error_message": None,
    }
    
    # 1. 快速缓存检查
    if settings.enable_cache:
        cache_key = generate_cache_key(request.app_key, request.text, request.context)
        cached_result = await cache.get(cache_key)
        
        if cached_result:
            logger.debug(f"Cache hit for app: {request.app_key}")
            log_data["recognized_intent"] = cached_result["intent"]
            log_data["confidence"] = cached_result["confidence"]
            log_data["processing_time_ms"] = (time.time() - start_time) * 1000
            log_data["recognition_chain"] = json.dumps([{"recognizer": "cache", "status": "success", "time_ms": log_data["processing_time_ms"]}])
            await save_log_async(log_data)
            cached_response = RecognizeResponse(**cached_result)
            cached_response.success = True
            return cached_response
    
    # 2. 批量获取配置
    context_data = await config_service.get_app_intent_context(request.app_key)
    
    if not context_data:
        # 处理配置缺失情况
        pass
    
    app_config = context_data["app_config"]
    categories = context_data["categories"]
    rules = context_data["rules"]
    
    # 3. 快速识别器链获取
    recognizer = await get_recognizer_chain_for_app(app_config)
    
    # 4. 执行识别
    result = None
    try:
        result = await recognizer.recognize(
            request.text,
            categories,
            rules,
            request.context,
        )
    except Exception as e:
        # 处理异常
        pass
    
    # 5. 构建响应和缓存
    # ...
```

### 5. 服务器配置优化

#### 5.1 FastAPI配置优化
```python
def create_app() -> FastAPI:
    """Create FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Intent Recognition Service for PLM Applications",
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        # 性能优化配置
        openapi_url=None,  # 禁用自动生成的OpenAPI文档
        default_response_class=Response,
    )
    
    # 中间件优化
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 其他配置...
    
    return app
```

## 性能优化效果预测

### 预期优化效果
1. **缓存优化**：减少90%的数据库查询
2. **数据库优化**：减少50%的数据库查询时间
3. **识别器链优化**：减少80%的识别器初始化时间
4. **API端点优化**：减少30%的请求处理时间

### 预期响应时间
- **优化前**：4137ms
- **优化后**：< 500ms
- **关键字匹配时间**：保持在7ms左右

## 实施步骤

1. **第一步**：实现内存缓存作为Redis fallback
2. **第二步**：优化数据库查询和配置缓存
3. **第三步**：优化识别器链缓存和初始化
4. **第四步**：优化API端点处理逻辑
5. **第五步**：测试和验证优化效果

## 监控和调试

### 性能监控指标
1. **请求处理时间**：总响应时间、各阶段时间分布
2. **缓存命中率**：Redis和内存缓存
3. **数据库查询时间**：各查询操作耗时
4. **识别器性能**：各识别器处理时间
5. **系统资源使用**：CPU、内存、网络

### 调试建议
1. **启用详细日志**：设置`logging_level=DEBUG`
2. **使用性能分析工具**：如`cProfile`或`py-spy`
3. **监控数据库查询**：启用SQLAlchemy的`echo=True`
4. **测试不同负载**：单请求、并发请求
5. **监控Redis连接**：确保缓存正常工作

## 结论

接口响应时间长的主要原因是：
1. **缓存失效**：Redis连接失败导致缓存禁用
2. **数据库查询**：每次请求都需要多次数据库查询
3. **识别器初始化**：首次请求需要初始化识别器链
4. **请求处理开销**：API端点处理逻辑复杂

通过实施上述优化措施，预计可以将响应时间从4137ms减少到500ms以下，同时保持关键字匹配的高性能。