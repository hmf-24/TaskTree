---
source: 工作文档
author: HMF
created: 2026-04-10
description: "TaskTree AI对话记忆功能完整文档，解决上下文延续问题"
tags:
  - Status/Done
  - Type/Work/SOP
  - Area/Lab
  - Tech/Python
---

# AI 对话记忆功能

## 功能概述

> [!info] 功能定位
> AI 对话记忆功能通过引入对话历史持久化和多场景 AI 助手，解决当前 AI 智能任务创建功能的核心痛点：每次对话都是全新开始，无法延续上下文，无法对现有任务进行分析和优化。

## 核心功能

### 1. 对话历史持久化
- 存储用户与 AI 的多轮对话消息
- 保持最近 30 条消息（15 轮对话）的上下文
- 支持对话列表查看和历史对话恢复

### 2. 任务分析助手
- 分析项目任务，识别瓶颈、冲突、风险
- 提供优化建议和可执行操作
- 支持持续对话，深入讨论分析结果

### 3. 任务修改助手
- 通过自然语言修改任务
- 支持相对时间表达（如"延后3天"）
- 支持批量操作

### 4. 项目规划助手
- 基于现有任务结构生成新任务建议
- 识别缺失的任务类型（测试、文档、部署等）
- 考虑团队负载和时间安排

## 技术架构

### 系统架构

```
前端层 (React + TypeScript)
├─ AIAssistantPanel (统一 AI 助手面板)
│  ├─ TaskCreatorMode (任务创建模式)
│  ├─ TaskAnalyzerMode (任务分析模式)
│  ├─ TaskModifierMode (任务修改模式)
│  └─ ProjectPlannerMode (项目规划模式)
├─ MessageBubble (消息气泡组件)
└─ ConversationHistoryDrawer (历史对话抽屉)

后端层 (FastAPI + SQLAlchemy)
├─ API Routes (conversations.py)
│  ├─ POST /conversations
│  ├─ POST /conversations/{id}/messages
│  ├─ GET /conversations
│  ├─ POST /conversations/{id}/analyze
│  ├─ POST /conversations/{id}/modify
│  └─ POST /conversations/{id}/plan
├─ Service Layer
│  ├─ AIConversationService (对话管理核心)
│  ├─ TaskAnalyzer (任务分析器)
│  ├─ TaskModifier (任务修改器)
│  └─ ProjectPlanner (项目规划器)
└─ LLMService (复用现有服务)

数据层 (SQLite)
└─ ai_conversations 表
```

### 数据模型

#### ai_conversations 表

```sql
CREATE TABLE ai_conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    project_id INTEGER NOT NULL,
    task_id INTEGER,
    conversation_type VARCHAR(20) NOT NULL,
    title VARCHAR(255),
    messages TEXT NOT NULL,  -- JSON 格式
    context_data TEXT,       -- JSON 格式
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL
);
```

**字段说明**：
- `conversation_type`: 对话类型（create/analyze/modify/plan）
- `messages`: 消息列表，JSON 格式存储
- `context_data`: 上下文数据，包含项目信息、任务数据等

## 核心服务

### 1. AIConversationService

**职责**：对话管理核心服务

**关键方法**：
- `create_conversation()`: 创建新对话
- `send_message()`: 发送消息并获取 AI 回复
- `build_context()`: 构建对话上下文
- `compress_messages()`: 压缩消息历史（保留最近30条）

**特性**：
- 自动加载对话历史
- 智能上下文构建（项目信息 + 任务数据）
- 消息自动压缩
- LLM 调用封装（支持重试）

### 2. TaskAnalyzer

> [!tip] 分析维度
> 任务分析器支持以下分析维度：

**分析维度**：
1. **任务瓶颈**：识别阻塞项目进度的关键任务
2. **时间冲突**：发现截止日期冲突或不合理的任务
3. **优先级问题**：指出优先级设置不合理的任务
4. **延期风险**：预测可能延期的任务
5. **资源分配**：分析任务负载是否均衡

**返回格式**：
```json
{
  "summary": "整体评估摘要",
  "issues": [
    {
      "type": "bottleneck|conflict|priority|risk|resource",
      "severity": "high|medium|low",
      "task_ids": [1, 2, 3],
      "description": "问题描述",
      "suggestion": "优化建议"
    }
  ],
  "recommendations": [
    {
      "action": "adjust_deadline|change_priority|add_resource",
      "task_id": 123,
      "details": "具体建议"
    }
  ],
  "risk_score": 65
}
```

### 3. TaskModifier

**职责**：任务修改器

**支持的修改类型**：
- `update_due_date`: 修改截止日期
- `update_priority`: 修改优先级
- `update_status`: 修改状态
- `update_description`: 修改描述
- `batch_update`: 批量修改

**特性**：
- 自然语言意图解析
- 相对日期解析（如"延后3天"）
- 批量操作支持
- 修改前确认机制

### 4. ProjectPlanner

**职责**：项目规划器

**功能**：
- 分析现有任务结构
- 识别缺失的任务类型
- 建议新任务的时间安排
- 考虑团队负载

## API 接口

### 后端 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/tasktree/conversations` | 创建新对话 |
| POST | `/api/v1/tasktree/conversations/{id}/messages` | 发送消息 |
| GET | `/api/v1/tasktree/conversations` | 获取对话列表 |
| GET | `/api/v1/tasktree/conversations/{id}` | 获取对话详情 |
| POST | `/api/v1/tasktree/conversations/{id}/analyze` | 任务分析 |
| POST | `/api/v1/tasktree/conversations/{id}/modify` | 任务修改 |
| POST | `/api/v1/tasktree/conversations/{id}/plan` | 项目规划 |
| DELETE | `/api/v1/tasktree/conversations/{id}` | 删除对话 |

### 前端 API

```typescript
export const conversationsAPI = {
  create: (data) => api.post('/conversations', data),
  sendMessage: (id, data) => api.post(`/conversations/${id}/messages`, data),
  list: (params) => api.get('/conversations', { params }),
  get: (id) => api.get(`/conversations/${id}`),
  analyze: (id, data) => api.post(`/conversations/${id}/analyze`, data),
  modify: (id, data) => api.post(`/conversations/${id}/modify`, data),
  plan: (id, data) => api.post(`/conversations/${id}/plan`, data),
  delete: (id) => api.delete(`/conversations/${id}`)
};
```

## 前端组件

### 1. AIAssistantPanel

**统一 AI 助手面板**，支持四种模式：

```typescript
interface AIAssistantPanelProps {
  projectId: number;
  mode: 'create' | 'analyze' | 'modify' | 'plan';
  taskId?: number;
  open: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}
```

**功能**：
- 对话初始化
- 消息发送和接收
- 操作按钮处理
- 历史对话加载
- 自动滚动到最新消息

### 2. MessageBubble

**消息气泡组件**，展示用户和 AI 的消息：

**特性**：
- 区分用户和 AI 消息样式
- ReactMarkdown 渲染
- 时间戳显示
- 操作按钮渲染

### 3. ConversationHistoryDrawer

**历史对话抽屉**，展示和管理历史对话：

**功能**：
- 对话列表加载
- 对话切换
- 按项目过滤

## 集成点

### 1. 项目详情页

```typescript
// ProjectDetail.tsx
<Button onClick={() => setAnalyzeOpen(true)}>
  AI 分析
</Button>

<AIAssistantPanel
  projectId={projectId}
  mode="analyze"
  open={analyzeOpen}
  onClose={() => setAnalyzeOpen(false)}
/>
```

### 2. 任务详情抽屉

```typescript
// TaskDetailDrawer.tsx
<Button onClick={() => setModifyOpen(true)}>
  AI 修改
</Button>

<AIAssistantPanel
  projectId={task.project_id}
  taskId={task.id}
  mode="modify"
  open={modifyOpen}
  onClose={() => setModifyOpen(false)}
/>
```

### 3. AI 智能创建

```typescript
// AITaskCreatorModal.tsx
<Button onClick={() => setHistoryOpen(true)}>
  历史对话
</Button>

<ConversationHistoryDrawer
  open={historyOpen}
  onClose={() => setHistoryOpen(false)}
  onSelect={loadConversation}
/>
```

## 错误处理

### LLM API 错误

| 错误类型 | 错误码 | 处理方式 |
|---------|--------|---------|
| 超时 | Timeout | 提示用户稍后重试 |
| 认证失败 | 401/403 | 提示检查 API Key 配置 |
| 速率限制 | 429 | 提示用户稍后重试 |
| 服务错误 | 500 | 显示友好的错误提示 |

### 重试机制

```python
async def _call_llm_with_retry(self, messages, max_retries=3):
    """LLM 调用重试机制（指数退避）"""
    for attempt in range(max_retries):
        try:
            return await self.llm_service.chat(messages)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)
```

## 性能优化

### 1. 消息压缩
- 保留最近 30 条消息
- 超过限制自动移除最早的消息

### 2. 上下文限制
- 最大 4000 tokens
- 超过限制自动压缩

### 3. 速率限制
- 每个用户每分钟最多 20 次 LLM 调用
- 防止滥用

### 4. 缓存机制
- 缓存常见的分析结果
- 避免重复调用 LLM API

## 安全特性

### 1. 权限控制
- 用户只能访问自己的对话
- 验证项目访问权限
- 只包含用户有权访问的任务数据

### 2. 数据加密
- 敏感对话内容加密存储
- API Key 加密存储

### 3. 审计日志
- 记录所有 AI 操作
- 包含用户 ID、操作类型、时间戳

## 测试覆盖

### 后端测试
- AIConversationService 单元测试
- TaskAnalyzer 单元测试
- TaskModifier 单元测试
- ProjectPlanner 单元测试
- API 端点集成测试

### 前端测试
- 组件渲染测试
- 用户交互测试
- API 调用测试

## 已知问题和修复

### Bug #23: Minimax API 响应解析错误

> [!bug] 问题描述
> - LLM 对话一直失败，即使 API 连接测试成功

**根本原因**：
- Minimax API 返回的 `content` 数组包含多个元素
- 第一个元素是 `{"type": "thinking", ...}` (思考过程)
- 第二个元素才是 `{"type": "text", "text": "实际回复"}` (实际回复)
- 原代码直接取 `content[0].get("text")` 导致获取到空字符串

**修复方案**：
```python
# 遍历 content 数组，查找 type="text" 的元素
for item in content:
    if item.get("type") == "text":
        return item.get("text", "")
```

**验证结果**：✅ 对话功能正常

## 相关文件

### 后端
- [[../tech/TECH_SOLUTION|AI 技术方案]] - AI 服务技术方案
- [[../tech/DATABASE|数据库设计]] - 数据库结构设计
- [[../reference/MEMORY_OUTLINE|记忆功能设计]] - 记忆功能架构设计
- `backend/app/api/v1/conversations.py` - API 路由
- `backend/app/services/ai_conversation_service.py` - 对话服务
- `backend/app/services/task_analyzer.py` - 任务分析器
- `backend/app/services/task_modifier.py` - 任务修改器
- `backend/app/services/project_planner.py` - 项目规划器
- `backend/app/services/README_AI_SERVICES.md` - 服务文档

### 前端
- `frontend/src/components/ai/AIAssistantPanel.tsx` - AI 助手面板
- `frontend/src/components/ai/MessageBubble.tsx` - 消息气泡
- `frontend/src/components/ai/ConversationHistoryDrawer.tsx` - 历史对话抽屉
- `frontend/src/api/index.ts` - API 调用

## 未来扩展

1. **语音交互**
   - 语音输入
   - 语音播报

2. **多模态支持**
   - 图片分析
   - 文档解析

3. **智能推荐**
   - 基于历史对话的智能推荐
   - 个性化建议

4. **协作功能**
   - 团队共享对话
   - 对话导出和分享
