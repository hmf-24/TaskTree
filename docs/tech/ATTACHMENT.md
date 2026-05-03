---
source: 工作文档
author: HMF
created: 2026-04-10
description: "TaskTree 任务附件管理功能技术文档，支持15种文件格式上传下载"
tags:
  - Status/Done
  - Type/Work/SOP
  - Area/Lab
  - Tech/Python
---

# 任务附件管理功能

## 功能概述

任务附件管理功能允许用户为每个任务上传、查看、下载和删除附件文件。支持多种常见文件格式，包括文档、图片、压缩包等。

## 支持的文件格式

系统支持以下 15 种文件格式：

### 文档类
- **Word**: `.doc`, `.docx`
- **PDF**: `.pdf`
- **文本**: `.txt`, `.md`
- **Excel**: `.xls`, `.xlsx`
- **PowerPoint**: `.ppt`, `.pptx`

### 图片类
- **常见格式**: `.jpg`, `.jpeg`, `.png`, `.gif`

### 压缩包类
- **压缩文件**: `.zip`, `.rar`

## 文件大小限制

- **后端限制**: 50MB
- **Nginx 限制**: 100MB
- **前端验证**: 50MB

## API 接口

### 1. 上传附件
```http
POST /api/v1/tasktree/attachments/tasks/{task_id}/attachments
Content-Type: multipart/form-data
Authorization: Bearer {token}

Body:
- file: 文件对象
```

**响应**:
```json
{
  "code": 201,
  "message": "上传成功",
  "data": {
    "id": 1,
    "task_id": 6,
    "user_id": 1,
    "filename": "文档.pdf",
    "file_path": "backend/uploads/attachments/6/20260424_abc123_文档.pdf",
    "file_size": 1024000,
    "mime_type": "application/pdf",
    "created_at": "2026-04-24T10:30:00"
  }
}
```

### 2. 获取附件列表
```http
GET /api/v1/tasktree/attachments/tasks/{task_id}/attachments
Authorization: Bearer {token}
```

**响应**:
```json
{
  "code": 200,
  "message": "获取成功",
  "data": [
    {
      "id": 1,
      "task_id": 6,
      "user_id": 1,
      "filename": "文档.pdf",
      "file_path": "backend/uploads/attachments/6/20260424_abc123_文档.pdf",
      "file_size": 1024000,
      "mime_type": "application/pdf",
      "created_at": "2026-04-24T10:30:00"
    }
  ]
}
```

### 3. 下载附件
```http
GET /api/v1/tasktree/attachments/{attachment_id}/download
Authorization: Bearer {token}
```

**响应**: 文件流（二进制数据）

### 4. 删除附件
```http
DELETE /api/v1/tasktree/attachments/{attachment_id}
Authorization: Bearer {token}
```

**响应**:
```json
{
  "code": 200,
  "message": "附件删除成功"
}
```

## 权限控制

所有附件操作都需要验证用户权限：
- 用户必须是任务所属项目的成员或所有者
- 通过 `get_task_with_access()` 函数验证权限
- 未授权访问返回 403 Forbidden

## 存储结构

### 文件存储路径
```
backend/uploads/attachments/{task_id}/{unique_filename}
```

### 文件名格式
```
{timestamp}_{uuid}_{original_filename}
```

示例：
```
20260424_abc123def456_项目文档.pdf
```

## 安全特性

### 1. 文件类型验证
- 白名单机制，只允许指定的 15 种文件格式
- 通过文件扩展名验证
- 前后端双重验证

### 2. 文件大小验证
- 前端验证：上传前检查文件大小
- 后端验证：接收文件后再次检查
- 超过限制返回 400 Bad Request

### 3. 文件名清理
- 移除路径分隔符（`/`, `\`）
- 防止路径遍历攻击
- 保留原始文件名的可读性

### 4. 权限验证
- 每个操作都验证用户权限
- 只有项目成员可以访问附件
- 防止未授权访问

## 前端组件

### AttachmentList 组件

位置：`frontend/src/components/task/AttachmentList.tsx`

**功能**：
- 显示附件列表
- 上传新附件
- 下载附件
- 删除附件

**使用方式**：
```tsx
<AttachmentList 
  taskId={taskId} 
  onUpdate={() => {
    // 附件更新后的回调
  }} 
/>
```

**UI 特性**：
- 文件图标显示
- 文件大小格式化（B/KB/MB）
- 上传时间格式化
- 上传者信息显示
- 加载状态和空状态
- 删除确认对话框

## 错误处理

### 常见错误码

| 错误码 | 说明 | 处理方式 |
|--------|------|---------|
| 400 | 文件类型不支持或文件过大 | 提示用户选择正确的文件 |
| 403 | 没有权限访问 | 提示用户权限不足 |
| 404 | 附件或任务不存在 | 提示资源不存在 |
| 500 | 服务器内部错误 | 提示用户稍后重试 |

### 错误提示示例

**文件类型错误**：
```
不支持的文件类型: exe
请上传以下格式的文件: doc, docx, pdf, txt, md, jpg, jpeg, png, gif, zip, rar, xls, xlsx, ppt, pptx
```

**文件大小错误**：
```
文件大小超过限制（最大 50MB）
```

## 测试覆盖

### 后端测试

**文件工具测试** (`test_file_utils.py`)：
- 文件类型验证
- 文件大小验证
- 文件名清理
- 唯一文件名生成

**API 端点测试** (`test_attachments.py`)：
- 上传附件
- 获取附件列表
- 下载附件
- 删除附件

**错误处理测试** (`test_attachments_error_handling.py`)：
- 无效文件类型
- 文件过大
- 权限验证
- 资源不存在

### 测试结果
- ✅ 20 个单元测试全部通过
- ✅ 覆盖所有核心功能
- ✅ 覆盖所有错误场景

## 性能优化

### 1. 文件存储
- 按任务 ID 分目录存储
- 避免单个目录文件过多
- 便于批量删除和管理

### 2. 数据库查询
- 按创建时间降序排序
- 支持分页（未来扩展）
- 索引优化（task_id 字段）

### 3. 前端优化
- 上传前客户端验证
- 减少不必要的服务器请求
- 文件列表自动刷新

## 未来扩展

### 可能的功能增强
1. **文件预览**
   - 图片在线预览
   - PDF 在线查看
   - 文档在线预览

2. **批量操作**
   - 批量上传
   - 批量下载
   - 批量删除

3. **版本控制**
   - 文件版本历史
   - 版本对比
   - 版本回滚

4. **高级搜索**
   - 按文件名搜索
   - 按文件类型筛选
   - 按上传者筛选

5. **存储优化**
   - 云存储集成（OSS/S3）
   - 文件压缩
   - 缩略图生成

## 配置说明

### Nginx 配置

在 `frontend/nginx.conf` 中配置文件上传大小限制：

```nginx
server {
    client_max_body_size 100M;
    proxy_read_timeout 300s;
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;
}
```

### 后端配置

在 `backend/app/utils/file_utils.py` 中配置：

```python
# 最大文件大小（字节）
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {
    'doc', 'docx', 'pdf', 'txt', 'md',
    'jpg', 'jpeg', 'png', 'gif',
    'zip', 'rar',
    'xls', 'xlsx', 'ppt', 'pptx'
}
```

## 故障排查

> [!TIP]
> 上传成功但列表不显示？检查后端API响应格式是否统一

### 问题：上传成功但列表不显示

**症状**：
- 后端日志显示 200 OK
- 文件已保存到服务器
- 前端列表为空

**原因**：
- 后端 API 响应格式不一致
- 前端期望 `{code: 200, data: [...]}`
- 后端直接返回 Pydantic 对象

**解决方案**：
- 统一使用 `MessageResponse` 格式
- 确保所有端点返回 `code` 字段

### 问题：文件上传失败（0 字节）

> [!WARNING]
> 使用 customRequest 导致文件流被读取后无法再次读取

**解决方案**：
- 使用 Ant Design Upload 的标准 `action` 属性
- 删除自定义上传逻辑

### 问题：大文件上传失败

> [!CAUTION]
> Nginx 默认限制 1MB，超时时间不足

**解决方案**：
- 增加 `client_max_body_size`
- 增加超时时间配置

## 总结

任务附件管理功能提供了完整的文件管理能力，包括：
- ✅ 15 种文件格式支持
- ✅ 完整的权限控制
- ✅ 前后端双重验证
- ✅ 友好的用户体验
- ✅ 完善的错误处理
- ✅ 全面的测试覆盖

该功能已经过充分测试，可以安全地用于生产环境。

---

## 相关文档

- [[tech/API]] - API 接口定义
- [[tech/DATABASE]] - 数据库设计
- [[tech/TECH_SOLUTION]] - 技术方案
