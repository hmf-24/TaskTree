---
source: 工作文档
author: HMF
created: 2026-04-10
description: "TaskTree API接口文档 v1.0，定义所有RESTful接口"
tags:
  - Status/Done
  - Type/Work/SOP
  - Area/Lab
  - Tech/Python
---

# API接口文档 v1.0

## 基础信息

> [!INFO]
> 基础路径：`/api/v1/tasktree` | 认证方式：Bearer Token (JWT)

| 项目 | 说明 |
|------|------|
| 基础路径 | `/api/v1/tasktree` |
| 认证方式 | Bearer Token (JWT) |
| 数据格式 | JSON |
| 错误格式 | `{ "code": 400, "message": "错误信息", "data": null }` |

---

## 通用响应格式

```json
{
  "code": 200,
  "message": "success",
  "data": { ... }
}
```

### HTTP状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 401 | 未授权（Token无效或过期） |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 500 | 服务器错误 |

---

## 认证接口

### 1. 用户注册

```
POST /auth/register
```

**请求体**：
```json
{
  "email": "user@example.com",
  "password": "password123",
  "nickname": "用户名"
}
```

**响应**：
```json
{
  "code": 201,
  "message": "注册成功",
  "data": {
    "id": 1,
    "email": "user@example.com",
    "nickname": "用户名"
  }
}
```

---

### 2. 用户登录

```
POST /auth/login
```

**请求体**：
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**响应**：
```json
{
  "code": 200,
  "message": "登录成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 604800
  }
}
```

---

### 3. 获取当前用户信息

```
GET /auth/me
```

**响应**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "email": "user@example.com",
    "nickname": "用户名",
    "avatar": "https://...",
    "created_at": "2026-04-11T00:00:00Z"
  }
}
```

---

### 4. 更新用户信息

```
PUT /auth/me
```

**请求体**：
```json
{
  "nickname": "新昵称",
  "avatar": "https://..."
}
```

---

### 5. 修改密码

```
PUT /auth/password
```

**请求体**：
```json
{
  "old_password": "旧密码",
  "new_password": "新密码"
}
```

---

## 项目接口

### 6. 创建项目

```
POST /projects
```

**请求头**：
```
Authorization: Bearer {token}
```

**请求体**：
```json
{
  "name": "项目名称",
  "description": "项目描述",
  "start_date": "2026-04-11",
  "end_date": "2026-06-11"
}
```

**响应**：
```json
{
  "code": 201,
  "message": "创建成功",
  "data": {
    "id": 1,
    "name": "项目名称",
    "description": "项目描述",
    "owner_id": 1,
    "start_date": "2026-04-11",
    "end_date": "2026-06-11",
    "status": "active",
    "is_archived": false,
    "created_at": "2026-04-11T00:00:00Z",
    "updated_at": "2026-04-11T00:00:00Z"
  }
}
```

---

### 7. 获取项目列表

```
GET /projects
```

**查询参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| status | string | 筛选状态：active/archived |
| page | int | 页码，默认1 |
| page_size | int | 每页数量，默认20 |
| sort_by | string | 排序字段：name/created_at/updated_at |
| order | string | 排序方向：asc/desc |

**响应**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [...],
    "total": 10,
    "page": 1,
    "page_size": 20
  }
}
```

---

### 8. 获取项目详情

```
GET /projects/{project_id}
```

**响应**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "name": "项目名称",
    "description": "项目描述",
    "owner_id": 1,
    "start_date": "2026-04-11",
    "end_date": "2026-06-11",
    "status": "active",
    "is_archived": false,
    "created_at": "2026-04-11T00:00:00Z",
    "updated_at": "2026-04-11T00:00:00Z",
    "owner": { ... },
    "members": [...],
    "task_count": 10,
    "completed_count": 5
  }
}
```

---

### 9. 更新项目

```
PUT /projects/{project_id}
```

**请求体**：
```json
{
  "name": "新名称",
  "description": "新描述",
  "start_date": "2026-04-11",
  "end_date": "2026-06-11"
}
```

---

### 10. 删除项目

```
DELETE /projects/{project_id}
```

**响应**：
```json
{
  "code": 200,
  "message": "删除成功",
  "data": null
}
```

---

### 11. 归档项目

```
POST /projects/{project_id}/archive
```

**请求体**：
```json
{
  "archived": true
}
```

---

### 12. 邀请成员

```
POST /projects/{project_id}/members
```

**请求体**：
```json
{
  "email": "member@example.com",
  "role": "editor"
}
```

**角色**：owner / editor / viewer

---

### 13. 移除成员

```
DELETE /projects/{project_id}/members/{user_id}
```

---

### 14. 更新成员角色

```
PUT /projects/{project_id}/members/{user_id}
```

**请求体**：
```json
{
  "role": "viewer"
}
```

---

## 任务接口

### 15. 创建任务

```
POST /projects/{project_id}/tasks
```

**请求体**：
```json
{
  "name": "任务名称",
  "description": "任务描述",
  "parent_id": null,
  "assignee_id": null,
  "priority": "medium",
  "start_date": "2026-04-11",
  "due_date": "2026-04-18",
  "estimated_time": 480
}
```

**响应**：
```json
{
  "code": 201,
  "message": "创建成功",
  "data": {
    "id": 1,
    "project_id": 1,
    "parent_id": null,
    "name": "任务名称",
    "description": "任务描述",
    "assignee_id": null,
    "status": "pending",
    "priority": "medium",
    "progress": 0,
    "estimated_time": 480,
    "actual_time": null,
    "start_date": "2026-04-11",
    "due_date": "2026-04-18",
    "sort_order": 0,
    "created_at": "2026-04-11T00:00:00Z",
    "updated_at": "2026-04-11T00:00:00Z"
  }
}
```

---

### 16. 获取任务树

```
GET /projects/{project_id}/tasks/tree
```

**响应**：
```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "id": 1,
      "name": "任务1",
      "status": "pending",
      "progress": 50,
      "children": [
        {
          "id": 2,
          "name": "子任务1",
          "status": "completed",
          "progress": 100,
          "children": []
        }
      ]
    }
  ]
}
```

---

### 17. 获取任务列表

```
GET /projects/{project_id}/tasks
```

**查询参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| parent_id | int | 父任务ID |
| status | string | 状态筛选 |
| priority | string | 优先级筛选 |
| assignee_id | int | 负责人筛选 |
| tag_ids | string | 标签筛选（逗号分隔） |
| page | int | 页码 |
| page_size | int | 每页数量 |

---

### 18. 获取任务详情

```
GET /tasks/{task_id}
```

**响应**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "project_id": 1,
    "parent_id": null,
    "name": "任务名称",
    "description": "任务描述",
    "assignee_id": 1,
    "status": "pending",
    "priority": "medium",
    "progress": 50,
    "estimated_time": 480,
    "actual_time": 240,
    "start_date": "2026-04-11",
    "due_date": "2026-04-18",
    "sort_order": 0,
    "created_at": "2026-04-11T00:00:00Z",
    "updated_at": "2026-04-11T00:00:00Z",
    "assignee": { ... },
    "children": [...],
    "tags": [...],
    "dependencies": [...],
    "comments": [...],
    "attachments": [...]
  }
}
```

---

### 19. 更新任务

```
PUT /tasks/{task_id}
```

**请求体**：
```json
{
  "name": "新名称",
  "description": "新描述",
  "assignee_id": 1,
  "status": "in_progress",
  "priority": "high",
  "progress": 60,
  "start_date": "2026-04-11",
  "due_date": "2026-04-18",
  "estimated_time": 480
}
```

---

### 20. 删除任务

```
DELETE /tasks/{task_id}
```

**查询参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| delete_children | bool | 是否同时删除子任务，默认false |

---

### 21. 移动任务

```
PUT /tasks/{task_id}/move
```

**请求体**：
```json
{
  "parent_id": 1,
  "sort_order": 0
}
```

---

### 22. 批量创建任务

```
POST /projects/{project_id}/tasks/batch
```

**请求体**：
```json
{
  "tasks": [
    { "name": "任务1" },
    { "name": "任务2" },
    { "name": "任务3" }
  ]
}
```

---

## 依赖关系接口

### 23. 创建依赖

```
POST /tasks/{task_id}/dependencies
```

**请求体**：
```json
{
  "dependent_task_id": 2
}
```

---

### 24. 删除依赖

```
DELETE /tasks/{task_id}/dependencies/{dependent_task_id}
```

---

### 25. 检查依赖

```
GET /tasks/{task_id}/dependencies/check
```

**响应**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "can_start": false,
    "blocked_by": [
      { "task_id": 1, "name": "前置任务" }
    ]
  }
}
```

---

## 标签接口

### 26. 创建标签

```
POST /projects/{project_id}/tags
```

**请求体**：
```json
{
  "name": "标签名",
  "color": "#FF5733"
}
```

---

### 27. 获取标签列表

```
GET /projects/{project_id}/tags
```

---

### 28. 更新标签

```
PUT /tags/{tag_id}
```

---

### 29. 删除标签

```
DELETE /tags/{tag_id}
```

---

### 30. 为任务添加标签

```
POST /tasks/{task_id}/tags
```

**请求体**：
```json
{
  "tag_ids": [1, 2, 3]
}
```

---

## 评论接口

### 31. 添加评论

```
POST /tasks/{task_id}/comments
```

**请求体**：
```json
{
  "content": "评论内容",
  "mentions": [1, 2]
}
```

---

### 32. 获取评论列表

```
GET /tasks/{task_id}/comments
```

---

### 33. 删除评论

```
DELETE /comments/{comment_id}
```

---

## 附件接口 (v1.0 表结构已预留，API 待开发)

### 34. 上传附件

> [!TODO]
> v1.0 待开发

```
POST /tasks/{task_id}/attachments
```

**请求体**：multipart/form-data

---

## 搜索接口 (v1.0 待开发)

### 44. 全局搜索

> ⚠️ v1.0 待开发

```
GET /search
```

---

## 错误响应示例

```json
{
  "code": 400,
  "message": "邮箱格式不正确",
  "data": null
}
```

```json
{
  "code": 401,
  "message": "Token已过期，请重新登录",
  "data": null
}
```

```json
{
  "code": 403,
  "message": "没有权限访问此项目",
  "data": null
}
```

```json
{
  "code": 404,
  "message": "任务不存在",
  "data": null
}
```

---

## 相关文档

- [[tech/ATTACHMENT]] - 附件管理功能
- [[tech/DATABASE]] - 数据库设计
- [[tech/SMART_REMINDER]] - 智能提醒系统