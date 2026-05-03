---
source: 工作文档
author: HMF
created: 2026-04-10
description: "TaskTree 任务附件管理功能完整文档，包含需求、设计、实现和测试"
tags:
  - Status/Done
  - Type/Work/SOP
  - Area/Lab
  - Tech/Python
---

# 任务附件管理功能

## 功能概述

> [!info] 功能定位
> 任务附件管理功能允许用户为每个任务上传、查看、下载和删除附件文件。支持多种常见文件格式，包括文档、图片、压缩包等。

## 需求说明

### 核心功能

> [!tip] 支持的文件格式
> - 文档：doc, docx, pdf, txt, md
> - 图片：jpg, jpeg, png, gif
> - 压缩包：zip, rar
> - 表格：xls, xlsx
> - 演示：ppt, pptx
   - 自动生成唯一文件名
   - 权限验证：只有项目成员可以上传

2. **查看附件列表**
   - 显示文件名、大小、上传时间、上传者
   - 按创建时间降序排列
   - 支持空状态展示

3. **下载附件**
   - 支持中文文件名
   - 正确的 MIME 类型
   - 权限验证

4. **删除附件**
   - 删除确认对话框
   - 同时删除物理文件和数据库记录
   - 权限验证

## 技术设计

### 后端实现

#### 数据模型

```python
class TaskAttachment(Base):
    __tablename__ = 'task_attachments'
    
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False, unique=True)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
```

#### API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/tasktree/attachments/tasks/{task_id}/attachments` | 上传附件 |
| GET | `/api/v1/tasktree/attachments/tasks/{task_id}/attachments` | 获取附件列表 |
| GET | `/api/v1/tasktree/attachments/{attachment_id}/download` | 下载附件 |
| DELETE | `/api/v1/tasktree/attachments/{attachment_id}` | 删除附件 |

#### 文件存储

- **存储路径**: `backend/uploads/attachments/{task_id}/`
- **文件名格式**: `{timestamp}_{uuid}_{original_filename}`
- **示例**: `20260424_abc123def456_项目文档.pdf`

### 前端实现

#### 组件结构

```
AttachmentList (附件列表组件)
├─ Upload (上传组件)
├─ List (列表展示)
│  ├─ FileOutlined (文件图标)
│  ├─ 文件信息 (名称、大小、时间)
│  └─ 操作按钮 (下载、删除)
└─ Empty (空状态)
```

#### 关键功能

1. **客户端验证**
   - 文件类型检查
   - 文件大小检查
   - 友好的错误提示

2. **上传处理**
   - 使用 Ant Design Upload 组件
   - 标准 action 属性上传
   - Authorization header 认证

3. **文件大小格式化**
   ```typescript
   const formatFileSize = (bytes: number): string => {
     if (bytes < 1024) return `${bytes} B`;
     if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
     return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
   };
   ```

## 安全特性

> [!warning] 安全注意事项
> 附件功能涉及文件上传和存储，需要注意以下安全事项：

1. **文件类型验证**
   - 白名单机制
   - 前后端双重验证

2. **文件大小限制**
   - 前端：50MB
   - 后端：50MB
   - Nginx：100MB

3. **权限控制**
   - 项目成员验证
   - 每个操作都检查权限

4. **文件名清理**
   - 移除路径分隔符
   - 防止路径遍历攻击

## 测试覆盖

### 后端测试（20个用例）

1. **文件工具测试** (`test_file_utils.py`)
   - 文件类型验证
   - 文件大小验证
   - 文件名清理
   - 唯一文件名生成

2. **API 端点测试** (`test_attachments.py`)
   - 上传附件
   - 获取附件列表
   - 下载附件
   - 删除附件

3. **错误处理测试** (`test_attachments_error_handling.py`)
   - 无效文件类型
   - 文件过大
   - 权限验证
   - 资源不存在

## 已知问题和修复

### Bug #24: 附件上传成功但列表不显示

> [!bug] 问题描述
> - 文件上传成功（后端日志显示 200 OK）
> - 前端列表不显示附件

**根本原因**：
- 后端附件 API 返回格式与其他 API 不一致
- 其他 API 返回 `{"code": 200, "data": {...}, "message": "..."}`
- 附件 API 直接返回 Pydantic 对象，没有 `code` 字段
- 前端 `fetchAttachments` 检查 `res.code === 200`，条件判断失败

**修复方案**：
修改 `backend/app/api/v1/attachments.py` 中的三个端点，统一使用 `MessageResponse` 格式：

1. **上传附件**：
   ```python
   return MessageResponse(
       code=201,
       message="上传成功",
       data={...}
   )
   ```

2. **获取列表**：
   ```python
   return MessageResponse(
       code=200,
       message="获取成功",
       data=[...]
   )
   ```

3. **删除附件**：
   ```python
   return MessageResponse(
       code=200,
       message="附件删除成功"
   )
   ```

**验证结果**：✅ 所有功能正常

## 配置说明

### Nginx 配置

```nginx
server {
    client_max_body_size 100M;
    proxy_read_timeout 300s;
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;
}
```

### 后端配置

```python
# backend/app/utils/file_utils.py
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

ALLOWED_EXTENSIONS = {
    'doc', 'docx', 'pdf', 'txt', 'md',
    'jpg', 'jpeg', 'png', 'gif',
    'zip', 'rar',
    'xls', 'xlsx', 'ppt', 'pptx'
}
```

## 使用示例

### 前端集成

```typescript
// 在任务详情抽屉中使用
<AttachmentList 
  taskId={taskId} 
  onUpdate={() => {
    // 附件更新后刷新任务详情
    fetchTaskDetail();
  }} 
/>
```

### API 调用

```typescript
// 上传附件
const formData = new FormData();
formData.append('file', file);
await attachmentsAPI.upload(taskId, file);

// 获取列表
const res = await attachmentsAPI.list(taskId);
const attachments = res.data;

// 下载附件
await attachmentsAPI.download(attachmentId);

// 删除附件
await attachmentsAPI.delete(attachmentId);
```

## 未来扩展

1. **文件预览**
   - 图片在线预览
   - PDF 在线查看

2. **批量操作**
   - 批量上传
   - 批量下载

3. **云存储集成**
   - OSS/S3 支持
   - CDN 加速

4. **版本控制**
   - 文件版本历史
   - 版本回滚

## 相关文件

### 后端
- [[../tech/ATTACHMENT|附件存储方案]] - 附件技术方案
- [[../tech/API|API 接口设计]] - API 接口定义
- [[../ tech/DATABASE |数据库设计]] - 数据库结构设计
- `backend/app/api/v1/attachments.py` - API 路由
- `backend/app/utils/file_utils.py` - 文件工具
- `backend/tests/test_attachments.py` - 测试文件

### 前端
- `frontend/src/components/task/AttachmentList.tsx` - 附件列表组件
- `frontend/src/api/index.ts` - API 调用
- `frontend/src/types/index.ts` - 类型定义
