# AI 对话记忆功能 - 后端服务

## 服务概览

本模块实现了 AI 对话记忆功能的四个核心服务类,用于支持多场景 AI 助手功能。

### 1. AIConversationService (ai_conversation_service.py)

**职责**: 对话管理核心服务

**主要功能**:
- 对话历史 CRUD 操作
- 上下文构建 (项目信息 + 任务数据)
- LLM 调用封装和重试机制
- 消息压缩 (保留最近30条)

**关键方法**:
- `create_conversation()`: 创建新对话
- `get_conversation()`: 获取对话详情 (验证权限)
- `list_conversations()`: 获取对话列表
- `add_message()`: 添加消息到对话历史
- `send_message()`: 发送消息并获取 AI 回复
- `build_context()`: 构建对话上下文
- `compress_messages()`: 压缩消息历史
- `delete_conversation()`: 删除对话

**配置参数**:
- `MAX_MESSAGES = 30`: 最多保留30条消息 (15轮对话)
- `MAX_CONTEXT_TOKENS = 4000`: 上下文 token 限制

**错误处理**:
- `LLMTimeoutError`: LLM 超时错误
- `LLMAuthError`: LLM 认证错误
- `LLMRateLimitError`: LLM 速率限制错误
- `LLMError`: LLM 调用错误基类

**重试机制**:
- 最多重试 3 次
- 指数退避策略 (2^attempt 秒)
- 超时和 5xx 错误重试,4xx 错误不重试

### 2. TaskAnalyzer (task_analyzer.py)

**职责**: 任务分析器

**主要功能**:
- 分析项目任务情况
- 识别任务瓶颈、时间冲突、优先级问题
- 预测延期风险
- 生成优化建议

**关键方法**:
- `analyze_project_tasks()`: 分析项目任务
- `_get_project_tasks()`: 获取项目所有任务
- `_build_analysis_prompt()`: 构建分析 prompt
- `_parse_analysis_response()`: 解析 LLM 分析响应
- `_fallback_analysis()`: 基础分析 (LLM 不可用时)

**分析维度**:
1. 任务瓶颈 (bottleneck)
2. 时间冲突 (conflict)
3. 优先级问题 (priority)
4. 延期风险 (risk)
5. 资源分配 (resource)

**返回格式**:
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
      "action": "adjust_deadline|change_priority|add_resource|split_task",
      "task_id": 123,
      "details": "具体建议"
    }
  ],
  "risk_score": 0-100
}
```

### 3. TaskModifier (task_modifier.py)

**职责**: 任务修改器

**主要功能**:
- 解析自然语言修改指令
- 生成修改操作
- 执行任务修改 (单个或批量)

**关键方法**:
- `parse_modification_intent()`: 解析修改意图
- `execute_modification()`: 执行修改操作
- `_parse_relative_date()`: 解析相对日期 (如"延后3天")
- `_identify_tasks_by_description()`: 根据描述识别任务
- `_fallback_intent_parse()`: 简单规则匹配 (LLM 不可用时)

**支持的修改类型**:
1. `update_due_date`: 修改截止日期
2. `update_priority`: 修改优先级
3. `update_status`: 修改状态
4. `update_description`: 修改描述
5. `batch_update`: 批量修改

**返回格式**:
```json
{
  "action": "update_due_date|update_priority|...",
  "task_ids": [123, 456],
  "params": {
    "due_date": "2024-12-31",
    "offset_days": 3,
    "priority": "high",
    "status": "in_progress"
  },
  "confirmation_message": "将任务 #123 的截止日期延后3天至 2024-12-31,是否确认?",
  "confidence": 0.9
}
```

### 4. ProjectPlanner (project_planner.py)

**职责**: 项目规划器

**主要功能**:
- 分析任务结构
- 识别缺失的任务类型
- 生成新任务建议
- 提供项目里程碑建议

**关键方法**:
- `analyze_and_plan()`: 分析项目并生成规划建议
- `_identify_missing_task_types()`: 识别缺失的任务类型
- `_suggest_task_timeline()`: 建议新任务的时间安排
- `_fallback_planning()`: 基础规划 (LLM 不可用时)

**识别的任务类型**:
- 测试 (test, testing, qa)
- 文档 (doc, documentation)
- 部署 (deploy, deployment)
- 代码审查 (review, code review)
- 设计 (design, ui, ux)
- 需求分析 (requirement)
- 性能优化 (performance, optimization)
- 安全 (security)
- 监控 (monitor, logging)

**返回格式**:
```json
{
  "summary": "规划建议摘要",
  "missing_tasks": [
    {
      "name": "任务名称",
      "description": "任务描述",
      "priority": "high|medium|low",
      "estimated_time": 120,
      "suggested_start_date": "2024-12-01",
      "suggested_due_date": "2024-12-15",
      "reason": "为什么需要这个任务"
    }
  ],
  "structure_improvements": [
    {
      "issue": "问题描述",
      "suggestion": "改进建议"
    }
  ],
  "milestones": [
    {
      "name": "里程碑名称",
      "target_date": "2024-12-31",
      "tasks": [1, 2, 3]
    }
  ]
}
```

## 使用示例

```python
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.llm_service import LLMService
from app.services.ai_conversation_service import AIConversationService
from app.services.task_analyzer import TaskAnalyzer
from app.services.task_modifier import TaskModifier
from app.services.project_planner import ProjectPlanner

# 创建 LLM 服务
llm_service = LLMService(
    provider="minimax",
    api_key="your_api_key",
    model="MiniMax-M2.7"
)

# 创建对话服务
conversation_service = AIConversationService(db_session, llm_service)

# 创建新对话
conversation = await conversation_service.create_conversation(
    user_id=1,
    project_id=1,
    conversation_type='analyze'
)

# 发送消息
result = await conversation_service.send_message(
    conversation_id=conversation.id,
    user_id=1,
    user_message="请分析这个项目的任务情况"
)

# 任务分析
analyzer = TaskAnalyzer(db_session, llm_service)
analysis = await analyzer.analyze_project_tasks(
    project_id=1,
    user_id=1,
    focus_areas=['bottleneck', 'risk']
)

# 任务修改
modifier = TaskModifier(db_session, llm_service)
intent = await modifier.parse_modification_intent(
    user_input="把任务 #123 延后3天",
    context_tasks=tasks
)
result = await modifier.execute_modification(intent)

# 项目规划
planner = ProjectPlanner(db_session, llm_service)
plan = await planner.analyze_and_plan(
    project_id=1,
    user_id=1,
    planning_goal="完善测试和文档"
)
```

## 依赖关系

```
AIConversationService
├── LLMService (复用现有)
├── AIConversation (模型)
├── Project (模型)
└── Task (模型)

TaskAnalyzer
├── LLMService
├── Project (模型)
└── Task (模型)

TaskModifier
├── LLMService
└── Task (模型)

ProjectPlanner
├── LLMService
├── Project (模型)
└── Task (模型)
```

## 错误处理

所有服务都实现了完善的错误处理:

1. **LLM 调用错误**: 自动重试 (最多3次),指数退避
2. **权限验证**: 验证用户是否有权访问对话/项目
3. **数据验证**: 验证输入参数的有效性
4. **后备方案**: LLM 不可用时使用基于规则的后备逻辑

## 性能优化

1. **消息压缩**: 自动保留最近30条消息,避免上下文过长
2. **任务限制**: 分析时最多处理50个任务,避免 prompt 过长
3. **异步操作**: 所有数据库操作都是异步的
4. **重试机制**: 智能重试,避免不必要的 API 调用

## 下一步

- [ ] 实现 API 路由层 (conversations.py)
- [ ] 实现前端组件 (AIAssistantPanel)
- [ ] 集成到现有页面 (ProjectDetail, TaskDetailDrawer)
- [ ] 编写单元测试和集成测试
