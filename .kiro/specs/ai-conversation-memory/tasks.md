# 实现计划: AI 对话记忆功能

## 概述

本实现计划将「AI 对话记忆功能」分解为可执行的编码任务。实现顺序遵循:数据库 → 后端服务 → API 接口 → 前端组件 → 集成测试。

**技术栈**:
- 后端: Python (FastAPI + SQLAlchemy + SQLite)
- 前端: TypeScript (React 18 + Ant Design + Zustand)
- LLM: 复用现有 LLMService

**优先级**:
- P0 (高优先级): 对话历史持久化、任务分析助手、持续对话模式
- P1 (中优先级): 任务修改助手、前端 UI 组件
- P2 (低优先级): 项目规划助手、性能优化、监控

## 任务列表

### 阶段 1: 数据库和模型层 (P0)

- [x] 1. 创建数据库表和模型
  - [x] 1.1 创建 ai_conversations 数据库表
    - 使用 Alembic 创建迁移脚本
    - 定义表结构:id, user_id, project_id, task_id, conversation_type, title, messages (TEXT/JSON), context_data (TEXT/JSON), created_at, updated_at
    - 创建外键约束:user_id → users.id (CASCADE), project_id → projects.id (CASCADE), task_id → tasks.id (SET NULL)
    - 创建索引:idx_ai_conversations_user (user_id), idx_ai_conversations_project (project_id), idx_ai_conversations_created (created_at)
    - _需求: 1.1, 1.2, 1.3, 1.6_
  
  - [x] 1.2 创建 SQLAlchemy 模型类
    - 在 backend/app/models/__init__.py 中定义 AIConversation 模型
    - 实现 messages_list property (JSON 序列化/反序列化)
    - 实现 context_dict property (JSON 序列化/反序列化)
    - 定义关联关系:user, project, task
    - _需求: 1.1, 1.2_
  
  - [x] 1.3 创建 Pydantic Schemas
    - 在 backend/app/schemas/__init__.py 中定义 MessageSchema, ConversationCreate, ConversationResponse, MessageCreate, MessageResponse
    - 定义 AnalyzeRequest, ModifyRequest, PlanRequest schemas
    - _需求: 1.1, 7.1, 7.2, 7.3_

- [x] 2. Checkpoint - 验证数据库迁移
  - 运行 alembic upgrade head 确保迁移成功
  - 验证表结构和索引创建正确
  - 确保所有测试通过,询问用户是否有问题

### 阶段 2: 后端核心服务 (P0)

- [ ] 3. 实现 AI_Conversation_Service
  - [ ] 3.1 创建 AIConversationService 类
    - 在 backend/app/services/ai_conversation_service.py 中创建服务类
    - 实现 __init__(db: AsyncSession, llm_service: LLMService)
    - 定义常量:MAX_MESSAGES = 30, MAX_CONTEXT_TOKENS = 4000
    - _需求: 1.1, 5.1_
  
  - [ ] 3.2 实现对话 CRUD 方法
    - 实现 create_conversation():创建新对话,初始化 messages 为空列表
    - 实现 get_conversation():获取对话详情,验证用户权限
    - 实现 list_conversations():获取对话列表,支持按 project_id 和 conversation_type 过滤
    - 实现 delete_conversation():删除对话,验证用户权限
    - _需求: 1.2, 1.3, 1.7, 10.1, 10.2_
  
  - [ ] 3.3 实现消息管理方法
    - 实现 add_message():添加消息到对话历史,更新 updated_at
    - 实现 compress_messages():保留最近 30 条消息,移除更早的消息
    - _需求: 1.3, 1.4, 1.5_
  
  - [ ] 3.4 实现上下文构建方法
    - 实现 build_context():获取项目信息、任务数据,构建上下文字典
    - 包含:project_name, task_count, completed_count, in_progress_count, pending_count
    - _需求: 5.2, 5.3_
  
  - [ ] 3.5 实现 LLM 调用封装
    - 实现 send_message():发送消息并获取 AI 回复
    - 实现 _build_llm_messages():根据 conversation_type 构建 LLM 消息列表
    - 实现 _call_llm_with_retry():带重试机制的 LLM 调用 (最多 3 次,指数退避)
    - 处理 LLM 错误:超时、认证、速率限制、服务不可用
    - _需求: 5.3, 8.1, 8.2, 8.3, 9.3, 9.5_
  
  - [ ]* 3.6 编写 AIConversationService 单元测试
    - 测试 create_conversation, get_conversation, list_conversations
    - 测试 add_message, compress_messages (验证 30 条限制)
    - 测试 verify_conversation_access (权限验证)
    - 使用 Mock LLMService

- [ ] 4. 实现 Task_Analyzer 服务
  - [ ] 4.1 创建 TaskAnalyzer 类
    - 在 backend/app/services/task_analyzer.py 中创建服务类
    - 实现 __init__(db: AsyncSession, llm_service: LLMService)
    - _需求: 2.1_
  
  - [ ] 4.2 实现任务分析方法
    - 实现 analyze_project_tasks():分析项目任务,返回结构化结果
    - 实现 _get_project_tasks():获取项目所有任务
    - 实现 _build_analysis_prompt():构建分析 prompt,包含任务详情
    - 实现 _parse_analysis_response():解析 LLM JSON 响应,提取 summary, issues, recommendations, risk_score
    - _需求: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_
  
  - [ ]* 4.3 编写 TaskAnalyzer 单元测试
    - 测试 analyze_project_tasks (Mock LLM 响应)
    - 测试 _parse_analysis_response (有效和无效 JSON)

- [ ] 5. 实现 Task_Modifier 服务
  - [ ] 5.1 创建 TaskModifier 类
    - 在 backend/app/services/task_modifier.py 中创建服务类
    - 实现 __init__(db: AsyncSession, llm_service: LLMService)
    - _需求: 3.1_
  
  - [ ] 5.2 实现意图解析方法
    - 实现 parse_modification_intent():解析自然语言修改指令
    - 实现 _build_modification_prompt():构建修改意图解析 prompt
    - 识别修改类型:update_due_date, update_priority, update_status, add_subtask, update_description, batch_update
    - 解析相对时间表达式 (如"延后 3 天")
    - _需求: 3.1, 3.2, 3.3, 3.4_
  
  - [ ] 5.3 实现修改执行方法
    - 实现 execute_modification():执行任务修改操作
    - 支持单个和批量修改
    - 返回结构化结果:success, failed, errors
    - 实现 _parse_relative_date():解析相对日期偏移
    - _需求: 3.5, 3.6, 3.7_
  
  - [ ]* 5.4 编写 TaskModifier 单元测试
    - 测试 parse_modification_intent (各种修改类型)
    - 测试 execute_modification (单个和批量)
    - 测试 _parse_relative_date

- [ ] 6. 实现 Project_Planner 服务
  - [ ] 6.1 创建 ProjectPlanner 类
    - 在 backend/app/services/project_planner.py 中创建服务类
    - 实现 __init__(db: AsyncSession, llm_service: LLMService)
    - _需求: 4.1_
  
  - [ ] 6.2 实现项目规划方法
    - 实现 analyze_and_plan():分析项目并生成规划建议
    - 实现 _identify_missing_tasks():识别缺失的任务类型
    - 实现 _suggest_task_timeline():建议新任务的时间安排
    - 实现 _build_planning_prompt():构建规划 prompt
    - _需求: 4.1, 4.2, 4.3, 4.4, 4.5_
  
  - [ ]* 6.3 编写 ProjectPlanner 单元测试
    - 测试 analyze_and_plan (Mock LLM 响应)
    - 测试 _identify_missing_tasks

- [ ] 7. Checkpoint - 验证后端服务
  - 运行所有后端单元测试,确保通过
  - 验证服务类可以正确实例化和调用
  - 确保所有测试通过,询问用户是否有问题

### 阶段 3: API 接口层 (P0)

- [ ] 8. 实现 Conversations API 路由
  - [ ] 8.1 创建 conversations.py 路由文件
    - 在 backend/app/api/v1/conversations.py 中创建路由
    - 导入必要的依赖:FastAPI, AsyncSession, schemas, services
    - 创建 APIRouter 实例
    - _需求: 7.1_
  
  - [ ] 8.2 实现对话管理接口
    - 实现 POST /conversations:创建新对话
    - 实现 GET /conversations:获取对话列表 (支持 project_id, conversation_type 过滤)
    - 实现 GET /conversations/{id}:获取对话详情
    - 实现 DELETE /conversations/{id}:删除对话
    - 所有接口验证用户身份 (get_current_user)
    - _需求: 7.1, 7.3, 7.4, 7.8, 10.1_
  
  - [ ] 8.3 实现消息发送接口
    - 实现 POST /conversations/{id}/messages:发送消息
    - 调用 AIConversationService.send_message()
    - 设置 60 秒超时
    - 返回 AI 回复和可执行操作
    - _需求: 7.2, 9.5_
  
  - [ ] 8.4 实现任务分析接口
    - 实现 POST /conversations/{id}/analyze:任务分析
    - 调用 TaskAnalyzer.analyze_project_tasks()
    - 支持 focus_areas 参数
    - _需求: 7.5, 2.7_
  
  - [ ] 8.5 实现任务修改接口
    - 实现 POST /conversations/{id}/modify:任务修改
    - 调用 TaskModifier.execute_modification()
    - 返回修改结果 (success_count, failed_count, errors)
    - _需求: 7.6_
  
  - [ ] 8.6 实现项目规划接口
    - 实现 POST /conversations/{id}/plan:项目规划
    - 调用 ProjectPlanner.analyze_and_plan()
    - 支持 planning_goal 参数
    - _需求: 7.7_
  
  - [ ] 8.7 注册路由到主应用
    - 在 backend/app/main.py 中导入 conversations router
    - 注册路由:app.include_router(conversations.router, prefix="/api/v1", tags=["conversations"])
    - _需求: 7.1_
  
  - [ ]* 8.8 编写 API 集成测试
    - 测试所有 API 端点 (create, list, get, delete, send_message, analyze, modify, plan)
    - 测试权限验证 (访问他人对话返回 404)
    - 测试错误处理 (无效参数返回 400)

- [ ] 9. Checkpoint - 验证 API 接口
  - 使用 Postman 或 curl 测试所有 API 端点
  - 验证请求/响应格式符合设计
  - 运行 API 集成测试,确保通过
  - 确保所有测试通过,询问用户是否有问题

### 阶段 4: 前端组件 (P1)

- [ ] 10. 创建前端类型定义
  - [ ] 10.1 定义 TypeScript 类型
    - 在 frontend/src/types/index.ts 中添加 Conversation, Message, Action 接口
    - 定义 CONVERSATION_TYPE_LABELS 常量
    - _需求: 6.1, 6.2_

- [ ] 11. 实现前端 API 客户端
  - [ ] 11.1 添加 conversationsAPI
    - 在 frontend/src/api/index.ts 中添加 conversationsAPI 对象
    - 实现方法:create, sendMessage, list, get, analyze, modify, plan, delete
    - 为 sendMessage, analyze, plan 设置 60 秒超时
    - _需求: 7.1-7.8_

- [ ] 12. 实现 AIAssistantPanel 组件
  - [ ] 12.1 创建 AIAssistantPanel 组件
    - 在 frontend/src/components/ai/AIAssistantPanel.tsx 中创建组件
    - 定义 Props:projectId, mode, taskId, open, onClose, onSuccess
    - 定义 State:conversationId, messages, inputValue, loading, historyOpen
    - _需求: 6.1, 6.2_
  
  - [ ] 12.2 实现对话初始化逻辑
    - 在 useEffect 中监听 open 变化,调用 conversationsAPI.create()
    - 根据 mode 发送初始消息 (analyze 模式自动分析)
    - _需求: 6.3, 6.4_
  
  - [ ] 12.3 实现消息发送逻辑
    - 实现 sendMessage():调用 conversationsAPI.sendMessage()
    - 更新 messages 状态,添加用户消息和 AI 回复
    - 显示加载状态 (loading spinner)
    - 处理错误:超时、认证、速率限制
    - _需求: 6.6, 6.8, 8.1, 8.2, 8.3_
  
  - [ ] 12.4 实现操作按钮处理
    - 实现 handleAction():处理 AI 回复中的可执行操作
    - 支持操作类型:apply_modification, create_tasks, view_analysis
    - 操作成功后调用 onSuccess() 刷新数据
    - _需求: 6.7_
  
  - [ ] 12.5 实现 UI 布局
    - 使用 Ant Design Drawer 组件
    - 布局:标题栏 (含历史对话按钮) + 消息列表 + 输入框
    - 消息列表支持滚动,自动滚动到最新消息
    - _需求: 6.5, 6.6_

- [ ] 13. 实现 MessageBubble 组件
  - [ ] 13.1 创建 MessageBubble 组件
    - 在 frontend/src/components/ai/MessageBubble.tsx 中创建组件
    - 定义 Props:message, onAction
    - 区分用户消息和 AI 消息样式
    - _需求: 6.5_
  
  - [ ] 13.2 实现消息渲染
    - 使用 ReactMarkdown 渲染消息内容
    - 显示消息时间戳
    - 显示用户/AI 图标
    - _需求: 6.5_
  
  - [ ] 13.3 实现操作按钮
    - 渲染 message.actions 中的操作按钮
    - 点击按钮调用 onAction(action)
    - _需求: 6.7_

- [ ] 14. 实现 ConversationHistoryDrawer 组件
  - [ ] 14.1 创建 ConversationHistoryDrawer 组件
    - 在 frontend/src/components/ai/ConversationHistoryDrawer.tsx 中创建组件
    - 定义 Props:open, onClose, onSelect
    - 定义 State:conversations, loading
    - _需求: 6.9_
  
  - [ ] 14.2 实现历史对话列表
    - 在 useEffect 中调用 conversationsAPI.list()
    - 使用 Ant Design List 组件渲染对话列表
    - 显示对话标题、类型标签、创建时间
    - 点击对话项调用 onSelect(conversationId)
    - _需求: 6.9_

- [ ] 15. Checkpoint - 验证前端组件
  - 在浏览器中测试 AIAssistantPanel 组件
  - 验证消息发送、接收、渲染正常
  - 验证历史对话加载和切换正常
  - 确保所有测试通过,询问用户是否有问题

### 阶段 5: 前端集成 (P1)

- [ ] 16. 集成到 ProjectDetail 页面
  - [ ] 16.1 添加 "AI 分析" 按钮
    - 在 frontend/src/pages/Project/ProjectDetail.tsx 中添加按钮
    - 按钮位置:页面顶部操作栏
    - 按钮图标:RobotOutlined
    - 点击按钮打开 AIAssistantPanel (mode="analyze")
    - _需求: 6.3_
  
  - [ ] 16.2 集成 AIAssistantPanel
    - 添加 State:aiMode, aiPanelOpen
    - 渲染 AIAssistantPanel 组件
    - onSuccess 回调:刷新任务列表和项目信息
    - _需求: 6.3_

- [ ] 17. 集成到 TaskDetailDrawer 组件
  - [ ] 17.1 添加 "AI 修改" 按钮
    - 在 frontend/src/components/task/TaskDetailDrawer.tsx 中添加按钮
    - 按钮位置:抽屉底部操作栏
    - 点击按钮打开 AIAssistantPanel (mode="modify", taskId=task.id)
    - _需求: 6.4_
  
  - [ ] 17.2 集成 AIAssistantPanel
    - 添加 State:aiPanelOpen
    - 渲染 AIAssistantPanel 组件
    - onSuccess 回调:刷新任务详情
    - _需求: 6.4_

- [ ] 18. 扩展 AITaskCreatorModal 组件
  - [ ] 18.1 添加对话历史支持
    - 在 frontend/src/components/task/AITaskCreatorModal.tsx 中添加对话历史功能
    - 复用 AIAssistantPanel 的对话逻辑
    - mode="create"
    - _需求: 6.2_

- [ ] 19. Checkpoint - 验证前端集成
  - 测试从 ProjectDetail 打开 AI 分析
  - 测试从 TaskDetailDrawer 打开 AI 修改
  - 测试 AITaskCreatorModal 的对话历史
  - 确保所有测试通过,询问用户是否有问题

### 阶段 6: 错误处理和优化 (P1)

- [ ] 20. 实现错误处理
  - [ ] 20.1 后端错误处理
    - 实现自定义异常类:LLMError, LLMTimeoutError, LLMAuthError, LLMRateLimitError
    - 在 API 层统一捕获异常,返回标准错误响应
    - 添加错误码:llm_timeout, llm_auth_error, llm_rate_limit, etc.
    - _需求: 8.1, 8.2, 8.3, 8.4, 8.5_
  
  - [ ] 20.2 前端错误处理
    - 创建 frontend/src/utils/errorMessages.ts
    - 定义 ERROR_MESSAGES 映射
    - 实现 getErrorMessage() 函数
    - 在 AIAssistantPanel 中使用 getErrorMessage() 显示友好提示
    - _需求: 8.1, 8.2, 8.3, 8.4, 8.5_

- [ ] 21. 实现性能优化
  - [ ] 21.1 实现速率限制
    - 在 AIConversationService 中实现 @rate_limit 装饰器
    - 限制:每个用户每分钟最多 20 次 LLM 调用
    - 使用内存缓存实现计数器
    - _需求: 9.3_
  
  - [ ] 21.2 实现对话历史清理
    - 创建后台任务:清理 30 天前的对话历史
    - 在 backend/app/main.py 中注册定时任务
    - _需求: 9.2_
  
  - [ ] 21.3 实现上下文压缩
    - 在 AIConversationService.send_message() 中检查 token 数量
    - 如果超过 4000 tokens,压缩到最近 20 条消息
    - _需求: 9.4_

- [ ] 22. 实现安全和权限控制
  - [ ] 22.1 实现权限验证
    - 在 AIConversationService 中实现 verify_conversation_access()
    - 在 AIConversationService 中实现 verify_project_access()
    - 在所有 API 端点中调用权限验证
    - _需求: 10.1, 10.2, 10.3_
  
  - [ ] 22.2 实现审计日志
    - 在 AIConversationService 中记录所有 AI 操作
    - 日志内容:user_id, operation_type, conversation_id, timestamp
    - _需求: 10.5_
  
  - [ ] 22.3 实现级联删除
    - 在 Project 删除时,级联删除相关对话历史
    - 验证外键约束 ON DELETE CASCADE 正确配置
    - _需求: 10.6_

- [ ] 23. Checkpoint - 验证错误处理和优化
  - 测试各种错误场景 (超时、认证失败、速率限制)
  - 验证错误提示友好且准确
  - 测试速率限制功能
  - 测试权限验证功能
  - 确保所有测试通过,询问用户是否有问题

### 阶段 7: 测试和文档 (P2)

- [ ] 24. 编写端到端测试
  - [ ]* 24.1 编写 E2E 测试
    - 在 frontend/e2e/ai-conversation.spec.ts 中编写测试
    - 测试场景:任务分析、任务修改、持续对话、历史对话加载
    - 使用 Playwright 进行测试

- [ ] 25. 编写 API 文档
  - [ ] 25.1 添加 API 文档注释
    - 在所有 API 端点中添加 docstring
    - 使用 FastAPI 自动生成 OpenAPI 文档
    - _需求: 7.1-7.8_

- [ ] 26. 最终验收测试
  - [ ] 26.1 完整功能测试
    - 测试所有用户故事场景
    - 验证所有验收标准
    - 测试跨浏览器兼容性
  
  - [ ] 26.2 性能测试
    - 使用 Locust 进行负载测试
    - 验证 API 响应时间 < 60 秒
    - 验证并发用户支持
    - _需求: 9.1, 9.3, 9.5_

- [ ] 27. 最终 Checkpoint
  - 运行所有测试套件 (单元测试、集成测试、E2E 测试)
  - 验证所有需求和验收标准已满足
  - 准备部署文档
  - 询问用户是否准备好部署

## 注意事项

1. **任务标记说明**:
   - `*` 标记的任务为可选任务 (主要是测试相关),可以跳过以加快 MVP 开发
   - 未标记的任务为必须完成的核心实现任务

2. **需求追溯**:
   - 每个任务都标注了对应的需求编号 (如 _需求: 1.1, 1.2_)
   - 确保所有需求都被任务覆盖

3. **Checkpoint 任务**:
   - 在关键阶段设置 Checkpoint,确保增量验证
   - Checkpoint 时运行测试,询问用户是否有问题

4. **依赖关系**:
   - 任务按照依赖顺序排列:数据库 → 后端 → API → 前端 → 集成
   - 每个阶段完成后再进入下一阶段

5. **测试策略**:
   - 单元测试标记为可选 (`*`),但强烈建议编写
   - 集成测试和 E2E 测试用于验证完整功能
   - 不使用 Property-Based Testing (功能依赖外部 LLM 服务,不适合 PBT)

6. **错误处理**:
   - 所有 LLM 调用都需要错误处理和重试机制
   - 前端需要显示用户友好的错误提示

7. **性能考虑**:
   - 实现速率限制,避免 API 滥用
   - 实现对话历史压缩,控制 token 消耗
   - 实现定期清理,避免数据库膨胀
