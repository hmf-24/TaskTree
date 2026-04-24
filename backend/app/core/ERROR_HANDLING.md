# 错误处理中间件文档

## 概述

本应用实现了全局错误处理中间件，确保所有错误返回适当的 HTTP 状态码和友好的错误消息。错误处理中间件在 `backend/app/core/exceptions.py` 中定义，并在 `backend/app/main.py` 中注册。

## 错误类型和状态码映射

### 1. 权限错误 (403 Forbidden)

**异常类型:**
- `PermissionDeniedError` (自定义异常)
- `PermissionError` (Python 内置异常，用于文件系统权限错误)

**使用场景:**
- 用户尝试访问无权限的资源
- 用户尝试执行无权限的操作
- 文件系统权限不足

**示例:**
```python
from app.core.exceptions import PermissionDeniedError

# 在路由处理函数中
if not user_has_permission:
    raise PermissionDeniedError("没有权限访问此资源")
```

**响应格式:**
```json
{
  "detail": "没有权限访问此资源"
}
```

### 2. 资源不存在 (404 Not Found)

**异常类型:**
- `ResourceNotFoundError` (自定义异常)
- `FileNotFoundError` (Python 内置异常，用于文件不存在)

**使用场景:**
- 请求的资源不存在于数据库
- 物理文件不存在于文件系统
- 附件记录存在但文件已被删除

**示例:**
```python
from app.core.exceptions import ResourceNotFoundError

# 在路由处理函数中
attachment = await db.get(TaskAttachment, attachment_id)
if not attachment:
    raise ResourceNotFoundError("附件不存在")
```

**响应格式:**
```json
{
  "detail": "附件不存在"
}
```

### 3. 验证错误 (400 Bad Request)

**异常类型:**
- `ValidationError` (自定义异常)
- `RequestValidationError` (FastAPI 内置异常)

**使用场景:**
- 文件类型不支持
- 文件大小超过限制
- 请求参数格式错误
- 业务逻辑验证失败

**示例:**
```python
from app.core.exceptions import ValidationError

# 在路由处理函数中
is_valid, message = validate_file_type(filename)
if not is_valid:
    raise ValidationError(message)
```

**响应格式:**
```json
{
  "detail": "不支持的文件类型: exe"
}
```

### 4. 文件系统错误 (500/404/403)

**异常类型:**
- `FileSystemError` (自定义异常)
- `OSError` (Python 内置异常)
- `IOError` (Python 内置异常)

**状态码映射:**
- `FileNotFoundError` → 404
- `PermissionError` → 403
- `OSError (errno=28)` → 507 (存储空间不足)
- 其他文件系统错误 → 500

**使用场景:**
- 文件读写失败
- 磁盘空间不足
- 文件系统权限问题

**示例:**
```python
# 文件系统错误会自动被中间件捕获
try:
    with open(file_path, "rb") as f:
        content = f.read()
except FileNotFoundError:
    # 自动返回 404
    raise
except PermissionError:
    # 自动返回 403
    raise
```

### 5. 数据库错误 (500 Internal Server Error)

**异常类型:**
- `SQLAlchemyError` (SQLAlchemy 异常基类)

**使用场景:**
- 数据库连接失败
- SQL 查询错误
- 事务提交失败
- 数据库约束违反

**响应格式:**
```json
{
  "detail": "数据库操作失败"
}
```

### 6. 通用错误 (500 Internal Server Error)

**异常类型:**
- `Exception` (所有未捕获的异常)

**使用场景:**
- 未预期的运行时错误
- 第三方库抛出的异常
- 编程错误

**响应格式:**
```json
{
  "detail": "服务器内部错误"
}
```

## 自定义异常类

### AppException (基类)

所有自定义异常的基类。

```python
class AppException(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
```

### PermissionDeniedError

权限拒绝异常，返回 403。

```python
raise PermissionDeniedError("没有权限访问此资源")
```

### ResourceNotFoundError

资源不存在异常，返回 404。

```python
raise ResourceNotFoundError("任务不存在")
```

### ValidationError

验证错误异常，返回 400。

```python
raise ValidationError("文件大小超过限制（最大 50MB）")
```

### FileSystemError

文件系统错误异常，可自定义状态码。

```python
raise FileSystemError("文件系统操作失败", status_code=500)
```

## 异常处理器注册

在 `backend/app/main.py` 中注册异常处理器：

```python
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    validation_exception_handler,
    sqlalchemy_exception_handler,
    file_system_exception_handler,
    generic_exception_handler
)

# 注册异常处理器
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
app.add_exception_handler(OSError, file_system_exception_handler)
app.add_exception_handler(IOError, file_system_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)
```

## 最佳实践

### 1. 使用自定义异常

优先使用自定义异常类，而不是直接抛出 `HTTPException`：

```python
# 推荐
raise ResourceNotFoundError("附件不存在")

# 不推荐
raise HTTPException(status_code=404, detail="附件不存在")
```

### 2. 提供清晰的错误消息

错误消息应该清晰、具体，帮助用户理解问题：

```python
# 好的错误消息
raise ValidationError("不支持的文件类型: exe。支持的类型: doc, docx, pdf, txt, md, jpg, jpeg, png, gif, zip, rar, xls, xlsx, ppt, pptx")

# 不好的错误消息
raise ValidationError("文件类型错误")
```

### 3. 记录详细错误信息

在异常处理器中记录详细的错误信息用于调试：

```python
async def file_system_exception_handler(request: Request, exc: Union[OSError, IOError]) -> JSONResponse:
    # 记录详细错误信息用于调试
    print(f"File system error: {str(exc)}")
    
    # 返回友好的错误消息给用户
    return JSONResponse(
        status_code=status_code,
        content={"detail": message}
    )
```

### 4. 不要泄露敏感信息

错误消息不应包含敏感信息（如数据库结构、文件路径等）：

```python
# 好的做法
raise ResourceNotFoundError("附件不存在")

# 不好的做法
raise ResourceNotFoundError(f"附件不存在: /var/www/uploads/secret_file.pdf")
```

## 测试

错误处理中间件的测试位于：
- `backend/tests/test_error_handling.py` - 单元测试
- `backend/tests/test_attachments_error_handling.py` - 集成测试

运行测试：

```bash
# 运行所有错误处理测试
pytest backend/tests/test_error_handling.py -v
pytest backend/tests/test_attachments_error_handling.py -v

# 运行特定测试
pytest backend/tests/test_error_handling.py::TestErrorHandlingRequirements::test_requirement_8_1_permission_errors_return_403 -v
```

## 需求映射

错误处理中间件满足以下需求：

- **需求 8.1**: 权限错误返回 403
- **需求 8.2**: 不支持的文件类型返回 400
- **需求 8.3**: 文件大小超限返回 400
- **需求 8.4**: 附件不存在返回 404
- **需求 8.5**: 物理文件不存在返回 404
- **需求 8.6**: 数据库操作失败返回 500
- **需求 8.7**: 文件系统错误返回适当的错误响应

## 故障排查

### 问题：异常没有被处理器捕获

**原因：** 异常处理器的注册顺序很重要。更具体的异常应该先注册。

**解决方案：** 确保异常处理器按照从具体到通用的顺序注册：

```python
app.add_exception_handler(AppException, app_exception_handler)  # 最具体
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
app.add_exception_handler(OSError, file_system_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)  # 最通用
```

### 问题：错误消息没有正确显示

**原因：** 响应格式不正确或前端没有正确解析。

**解决方案：** 确保所有异常处理器返回统一的 JSON 格式：

```python
{
  "detail": "错误消息"
}
```

### 问题：测试环境中异常处理器不工作

**原因：** TestClient 可能有自己的异常处理逻辑。

**解决方案：** 在测试中创建独立的 FastAPI 应用实例并注册异常处理器。

## 扩展

如果需要添加新的错误类型：

1. 在 `backend/app/core/exceptions.py` 中定义新的异常类
2. 创建对应的异常处理器函数
3. 在 `backend/app/main.py` 中注册异常处理器
4. 在 `backend/tests/test_error_handling.py` 中添加测试

示例：

```python
# 1. 定义异常类
class RateLimitExceededError(AppException):
    """速率限制超出异常 - 返回 429"""
    def __init__(self, message: str = "请求过于频繁"):
        super().__init__(message, status_code=status.HTTP_429_TOO_MANY_REQUESTS)

# 2. 创建处理器（可选，如果使用 AppException 基类处理器）
async def rate_limit_exception_handler(request: Request, exc: RateLimitExceededError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message}
    )

# 3. 注册处理器
app.add_exception_handler(RateLimitExceededError, rate_limit_exception_handler)

# 4. 使用
raise RateLimitExceededError("请求过于频繁，请稍后再试")
```
