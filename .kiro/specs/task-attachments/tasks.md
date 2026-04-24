# Implementation Plan: Task Attachments

## Overview

实现任务附件功能，包括文件上传、下载、删除和列表查询。后端使用 Python FastAPI 实现 RESTful API，前端使用 TypeScript React 实现用户界面。系统支持多种文件类型（文档、图片、压缩包等），提供完整的权限控制和文件生命周期管理。

## Tasks

- [x] 1. 实现后端文件验证和存储核心功能
  - [x] 1.1 创建文件验证工具函数
    - 在 `backend/app/utils/` 目录下创建 `file_utils.py`
    - 实现 `validate_file_type()` 函数：检查文件扩展名是否在允许列表中（doc, docx, pdf, txt, md, jpg, jpeg, png, gif, zip, rar, xls, xlsx, ppt, pptx）
    - 实现 `validate_file_size()` 函数：检查文件大小是否不超过 50MB
    - 实现 `sanitize_filename()` 函数：清理文件名中的特殊字符
    - 实现 `generate_unique_filename()` 函数：生成包含时间戳、UUID 和原始文件名的唯一文件名
    - _Requirements: 1.2, 1.3, 1.4, 1.5, 1.6, 5.1, 5.2, 5.3, 7.1, 7.2, 7.3, 7.4, 7.5_

  - [ ]* 1.2 编写文件验证函数的属性测试
    - **Property 2: File Type Validation**
    - **Validates: Requirements 1.2, 1.3, 7.1, 7.2, 7.3, 7.4, 7.5, 8.2**
    - 使用 Hypothesis 库编写属性测试
    - 测试任意允许扩展名的文件应被接受
    - 测试任意不允许扩展名的文件应被拒绝
    - 测试扩展名检查不区分大小写

  - [ ]* 1.3 编写文件大小验证的属性测试
    - **Property 3: File Size Validation**
    - **Validates: Requirements 1.4, 1.5, 8.3**
    - 测试任意不超过 50MB 的文件应被接受
    - 测试任意超过 50MB 的文件应被拒绝

  - [ ]* 1.4 编写文件名生成唯一性的属性测试
    - **Property 4: Filename Generation Completeness**
    - **Property 9: File Path Uniqueness**
    - **Validates: Requirements 1.6, 5.1, 5.2, 5.3, 5.4, 5.5**
    - 测试生成的文件名包含时间戳、UUID 和原始文件名三个组件
    - 测试多次调用生成不同的文件名

- [x] 2. 实现后端附件 API 端点
  - [x] 2.1 创建附件路由文件和 Schema
    - 在 `backend/app/api/v1/` 目录下创建 `attachments.py` 路由文件
    - 在 `backend/app/schemas/__init__.py` 中添加 `AttachmentListResponse` Schema（包含 attachments 列表和 total 字段）
    - 创建 APIRouter 实例并配置路由前缀
    - _Requirements: 1.10, 2.4, 2.5_

  - [x] 2.2 实现上传附件端点 POST /api/v1/tasks/{task_id}/attachments
    - 使用 `UploadFile` 接收文件上传
    - 调用 `get_task_with_access()` 验证用户权限
    - 调用 `validate_file_type()` 和 `validate_file_size()` 验证文件
    - 调用 `generate_unique_filename()` 生成唯一文件名
    - 创建目录 `backend/uploads/attachments/{task_id}/`（如果不存在）
    - 保存文件到文件系统
    - 创建 `TaskAttachment` 数据库记录（包含 task_id, user_id, filename, file_path, file_size, mime_type）
    - 返回 `AttachmentResponse`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.10, 6.1_

  - [x] 2.3 实现查询附件列表端点 GET /api/v1/tasks/{task_id}/attachments
    - 调用 `get_task_with_access()` 验证用户权限
    - 查询该任务的所有附件记录
    - 按创建时间降序排序
    - 返回 `AttachmentListResponse`（包含 attachments 列表和 total 字段）
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 2.4 实现下载附件端点 GET /api/v1/attachments/{attachment_id}/download
    - 查询附件记录并验证存在性
    - 通过附件的 task_id 调用 `get_task_with_access()` 验证用户权限
    - 验证物理文件存在
    - 使用 `FileResponse` 返回文件流
    - 设置 Content-Disposition header 为 "attachment; filename={encoded_filename}"
    - 设置正确的 MIME type
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8_

  - [x] 2.5 实现删除附件端点 DELETE /api/v1/attachments/{attachment_id}
    - 查询附件记录并验证存在性
    - 通过附件的 task_id 调用 `get_task_with_access()` 验证用户权限
    - 删除物理文件（如果存在）
    - 删除数据库记录
    - 提交事务
    - 返回成功消息
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

  - [ ]* 2.6 编写上传下载往返一致性的属性测试
    - **Property 5: Upload Round-Trip Preservation**
    - **Validates: Requirements 1.8, 1.10, 3.5, 3.8**
    - 测试上传文件后立即下载，内容和文件名应保持一致
    - 使用 Hypothesis 生成随机文件内容和文件名

  - [ ]* 2.7 编写附件元数据完整性的属性测试
    - **Property 6: Metadata Completeness**
    - **Validates: Requirements 1.9, 1.10, 2.5**
    - 测试成功上传后，数据库记录包含所有必需字段
    - 测试响应包含所有元数据字段

  - [ ]* 2.8 编写查询完整性和排序的属性测试
    - **Property 7: Query Completeness and Ordering**
    - **Validates: Requirements 2.2, 2.3, 2.4**
    - 测试查询返回的附件数量与 total 字段一致
    - 测试附件按创建时间降序排列

  - [ ]* 2.9 编写删除完整性的属性测试
    - **Property 10: Delete Completeness**
    - **Validates: Requirements 4.3, 4.4, 4.6**
    - 测试删除操作后，物理文件和数据库记录都不存在

- [x] 3. 集成附件路由到主应用
  - [x] 3.1 注册附件路由
    - 在 `backend/app/main.py` 中导入 `attachments` 路由
    - 使用 `app.include_router()` 注册路由，前缀为 `/api/v1`
    - _Requirements: 所有 API 端点_

  - [x] 3.2 添加错误处理中间件
    - 确保文件系统错误返回适当的 HTTP 状态码
    - 确保权限错误返回 403
    - 确保资源不存在返回 404
    - 确保验证错误返回 400
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7_

  - [ ]* 3.3 编写访问控制一致性的属性测试
    - **Property 1: Access Control Consistency**
    - **Validates: Requirements 1.1, 2.1, 3.2, 4.2**
    - 测试所有附件操作都进行权限验证
    - 测试无权限用户的操作被拒绝

  - [ ]* 3.4 编写错误响应一致性的属性测试
    - **Property 12: Error Response Consistency**
    - **Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5**
    - 测试不同错误场景返回正确的 HTTP 状态码

- [x] 4. Checkpoint - 后端功能验证
  - 使用 Postman 或 curl 测试所有 API 端点
  - 验证文件上传、下载、删除功能正常
  - 验证权限控制正确
  - 验证错误处理符合预期
  - 确保所有测试通过，询问用户是否有问题

- [ ] 5. 实现前端附件管理 UI 组件
  - [x] 5.1 创建附件列表组件
    - 在 `frontend/src/components/task/` 目录下创建 `AttachmentList.tsx`
    - 使用 Ant Design 的 `List` 组件展示附件列表
    - 显示文件名、文件大小、上传时间、上传者
    - 提供下载和删除按钮
    - 实现文件大小格式化函数（字节转 KB/MB）
    - _Requirements: 2.2, 2.3, 2.4, 2.5_

  - [x] 5.2 创建附件上传组件
    - 在 `AttachmentList.tsx` 中集成 Ant Design 的 `Upload` 组件
    - 配置 `beforeUpload` 钩子进行客户端文件验证（类型和大小）
    - 配置 `customRequest` 实现自定义上传逻辑
    - 显示上传进度
    - 上传成功后刷新附件列表
    - 显示友好的错误提示
    - _Requirements: 1.2, 1.3, 1.4, 1.5, 8.2, 8.3_

  - [x] 5.3 实现附件 API 调用函数
    - 在 `frontend/src/api/index.ts` 中添加 `attachmentsAPI` 对象
    - 实现 `upload(taskId, file)` 方法：使用 FormData 上传文件
    - 实现 `list(taskId)` 方法：获取附件列表
    - 实现 `download(attachmentId)` 方法：触发浏览器下载
    - 实现 `delete(attachmentId)` 方法：删除附件
    - _Requirements: 所有 API 端点_

  - [x] 5.4 集成附件组件到任务详情抽屉
    - 在 `frontend/src/components/task/TaskDetailDrawer.tsx` 中导入 `AttachmentList` 组件
    - 在评论区下方添加附件区域
    - 添加 "附件" 标题和分隔线
    - 传递 `taskId` 属性到 `AttachmentList` 组件
    - _Requirements: 所有前端功能_

  - [ ]* 5.5 编写前端组件单元测试
    - 测试附件列表正确渲染
    - 测试上传组件文件验证逻辑
    - 测试下载和删除操作触发正确的 API 调用

- [x] 6. 实现前端类型定义和常量
  - [x] 6.1 添加附件类型定义
    - 在 `frontend/src/types/index.ts` 中添加 `Attachment` 接口
    - 定义字段：id, task_id, user_id, filename, file_path, file_size, mime_type, created_at
    - _Requirements: 1.10, 2.5_

  - [x] 6.2 添加文件验证常量
    - 在 `frontend/src/constants/index.ts` 中添加 `ALLOWED_FILE_EXTENSIONS` 常量
    - 添加 `MAX_FILE_SIZE` 常量（50MB）
    - 添加 `FILE_TYPE_LABELS` 映射（用于显示友好的文件类型名称）
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 1.4, 1.5_

- [ ] 7. 实现文件下载功能
  - [x] 7.1 实现前端下载辅助函数
    - 在 `frontend/src/utils/` 目录下创建 `download.ts`
    - 实现 `downloadFile(url, filename)` 函数：创建隐藏的 `<a>` 标签触发下载
    - 处理中文文件名编码问题
    - _Requirements: 3.5, 3.6, 3.7_

  - [x] 7.2 在附件列表中集成下载功能
    - 为每个附件添加下载按钮（使用 `DownloadOutlined` 图标）
    - 点击下载按钮时调用 `attachmentsAPI.download()`
    - 显示下载进度提示
    - 处理下载错误
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8_

- [ ] 8. 实现附件删除确认和权限控制
  - [x] 8.1 添加删除确认对话框
    - 使用 Ant Design 的 `Modal.confirm()` 显示删除确认
    - 显示文件名和警告信息
    - 确认后调用 `attachmentsAPI.delete()`
    - 删除成功后刷新附件列表
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

  - [x] 8.2 实现前端权限控制
    - 根据当前用户权限显示/隐藏删除按钮
    - 只有附件上传者或项目管理员可以删除附件
    - 显示友好的权限错误提示
    - _Requirements: 4.2, 8.1_

- [ ] 9. 优化用户体验和错误处理
  - [x] 9.1 添加加载状态和空状态
    - 附件列表加载时显示 Skeleton 占位符
    - 无附件时显示友好的空状态提示
    - 上传中显示进度条
    - _Requirements: 用户体验_

  - [x] 9.2 实现全面的错误处理
    - 捕获网络错误并显示友好提示
    - 捕获文件验证错误并显示具体原因
    - 捕获权限错误并显示相应提示
    - 捕获服务器错误并显示通用错误消息
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7_

  - [~] 9.3 添加文件预览功能（可选增强）
    - 为图片类型附件添加预览功能
    - 使用 Ant Design 的 `Image.PreviewGroup` 组件
    - 点击图片附件时显示大图预览
    - _Requirements: 用户体验增强_

- [ ] 10. 集成测试和文档
  - [ ]* 10.1 编写端到端集成测试
    - 测试完整的上传-查询-下载-删除流程
    - 测试权限控制在整个流程中的正确性
    - 测试错误场景的处理

  - [~] 10.2 更新 API 文档
    - 在 `docs/技术/API接口.md` 中添加附件相关端点文档
    - 包含请求参数、响应格式、错误码说明
    - 添加使用示例
    - _Requirements: 文档_

  - [~] 10.3 添加用户使用说明
    - 在项目文档中添加附件功能使用指南
    - 说明支持的文件类型和大小限制
    - 提供常见问题解答
    - _Requirements: 文档_

- [~] 11. Final Checkpoint - 完整功能验证
  - 在开发环境中测试完整的附件管理流程
  - 验证前后端集成正常
  - 验证所有边界情况和错误处理
  - 验证用户体验流畅
  - 确保所有测试通过，询问用户是否有问题

## Notes

- 任务标记 `*` 的为可选测试任务，可跳过以加快 MVP 开发
- 每个任务都引用了具体的需求编号，确保可追溯性
- Checkpoint 任务用于阶段性验证，确保增量开发质量
- 属性测试验证通用正确性属性，单元测试验证具体示例和边界情况
- 前端和后端任务分离，可以并行开发
- 文件存储路径格式：`backend/uploads/attachments/{task_id}/{timestamp}_{uuid}_{filename}`
- 支持的文件类型：doc, docx, pdf, txt, md, jpg, jpeg, png, gif, zip, rar, xls, xlsx, ppt, pptx
- 最大文件大小：50MB
