# Requirements Document

## Introduction

本文档定义了 TaskTree 项目的「AI 对话记忆功能」需求。该功能旨在解决当前 AI 智能任务创建功能的核心痛点：每次对话都是全新开始，无法延续上下文，无法对现有任务进行分析和优化。

通过引入对话历史持久化和多场景 AI 助手，用户可以：
- 与 AI 进行多轮持续对话，保持上下文记忆
- 分析现有任务，获得优化建议
- 通过自然语言修改任务
- 基于现有任务结构规划新任务

## Glossary

- **AI_Conversation_Service**: AI 对话服务，负责管理对话历史、调用 LLM API、解析响应
- **Conversation_History**: 对话历史，存储用户与 AI 的多轮对话消息
- **Task_Analyzer**: 任务分析器，分析现有任务并生成优化建议
- **Task_Modifier**: 任务修改器，解析自然语言并执行任务修改操作
- **Project_Planner**: 项目规划器，基于现有任务结构生成新任务建议
- **Conversation_Context**: 对话上下文，包含项目信息、任务数据、用户偏好等
- **LLM_Service**: 大模型服务，已有的 LLM 调用封装
- **Database**: SQLite 数据库，用于持久化对话历史

## Requirements

### Requirement 1: 对话历史持久化

**User Story:** 作为用户，我希望 AI 能记住之前的对话内容，这样我就不需要重复描述上下文信息。

#### Acceptance Criteria

1. THE Database SHALL 存储对话历史记录，包含对话 ID、用户 ID、项目 ID、对话类型、消息列表、创建时间和更新时间
2. WHEN 用户发起新对话时，THE AI_Conversation_Service SHALL 创建新的对话记录并返回对话 ID
3. WHEN 用户在现有对话中发送消息时，THE AI_Conversation_Service SHALL 将消息追加到对话历史中
4. THE AI_Conversation_Service SHALL 保持最近 30 条消息（15 轮对话）的上下文
5. WHEN 对话消息超过 30 条时，THE AI_Conversation_Service SHALL 自动移除最早的消息
6. THE Database SHALL 为对话历史表创建索引，包含 user_id、project_id 和 created_at 字段
7. WHEN 用户请求历史对话列表时，THE AI_Conversation_Service SHALL 返回按时间倒序排列的对话摘要

### Requirement 2: 任务分析助手

**User Story:** 作为用户，我希望 AI 能分析我的现有任务，给出优化建议，这样我就能更好地管理项目进度。

#### Acceptance Criteria

1. WHEN 用户请求任务分析时，THE Task_Analyzer SHALL 获取项目的所有任务数据
2. THE Task_Analyzer SHALL 调用 LLM_Service 分析任务，识别以下问题：任务瓶颈、时间冲突、优先级不合理、延期风险
3. THE Task_Analyzer SHALL 返回结构化的分析结果，包含问题列表、优化建议、风险评估
4. WHEN 分析发现逾期任务时，THE Task_Analyzer SHALL 在分析结果中标记逾期天数
5. WHEN 分析发现时间冲突时，THE Task_Analyzer SHALL 在分析结果中列出冲突的任务对
6. THE Task_Analyzer SHALL 为每个建议生成可执行的操作建议（如"调整截止日期"、"提高优先级"）
7. THE Task_Analyzer SHALL 支持持续对话模式，用户可以针对分析结果提出进一步问题

### Requirement 3: 任务修改助手

**User Story:** 作为用户，我希望通过自然语言告诉 AI 如何修改任务，而不需要手动打开表单编辑。

#### Acceptance Criteria

1. WHEN 用户输入任务修改指令时，THE Task_Modifier SHALL 解析自然语言意图
2. THE Task_Modifier SHALL 识别以下修改类型：修改截止日期、修改优先级、修改状态、添加子任务、修改描述
3. WHEN 修改指令涉及相对时间（如"延后 3 天"）时，THE Task_Modifier SHALL 正确计算新的日期
4. WHEN 修改指令涉及批量操作（如"把所有高优先级任务延后一周"）时，THE Task_Modifier SHALL 识别并执行批量修改
5. THE Task_Modifier SHALL 在执行修改前向用户确认修改内容
6. WHEN 用户确认修改时，THE Task_Modifier SHALL 调用任务 API 执行修改操作
7. IF 修改操作失败，THEN THE Task_Modifier SHALL 返回错误信息并建议用户手动修改

### Requirement 4: 项目规划助手

**User Story:** 作为用户，我希望 AI 能基于现有任务结构帮我规划新任务，识别缺失的任务环节。

#### Acceptance Criteria

1. WHEN 用户请求项目规划时，THE Project_Planner SHALL 分析现有任务的结构和依赖关系
2. THE Project_Planner SHALL 识别项目中缺失的任务类型（如测试任务、文档任务、部署任务）
3. THE Project_Planner SHALL 基于现有任务的时间安排建议新任务的开始和截止日期
4. THE Project_Planner SHALL 考虑团队负载，避免在高负载时段安排新任务
5. THE Project_Planner SHALL 返回结构化的任务建议列表，包含任务名称、描述、优先级、预估工时、时间安排
6. WHEN 用户选择采纳建议时，THE Project_Planner SHALL 调用任务创建 API 批量创建任务
7. THE Project_Planner SHALL 支持持续对话模式，用户可以要求调整规划方案

### Requirement 5: 持续对话模式

**User Story:** 作为用户，我希望在一个会话中完成多个操作，AI 能记住我之前说过的内容。

#### Acceptance Criteria

1. THE AI_Conversation_Service SHALL 支持四种对话类型：任务创建、任务分析、任务修改、项目规划
2. WHEN 用户发起对话时，THE AI_Conversation_Service SHALL 加载对话上下文，包含项目信息和相关任务数据
3. THE AI_Conversation_Service SHALL 在每次 LLM 调用时包含完整的对话历史（最多 30 条消息）
4. WHEN 用户切换对话主题时，THE AI_Conversation_Service SHALL 识别主题变化并更新对话类型
5. THE AI_Conversation_Service SHALL 在对话中自动引用之前提到的任务（如"刚才分析的那个任务"）
6. WHEN 对话超过 15 轮时，THE AI_Conversation_Service SHALL 提示用户可以开始新对话
7. THE AI_Conversation_Service SHALL 支持用户手动结束对话并保存对话记录

### Requirement 6: 前端交互界面

**User Story:** 作为用户，我希望有一个统一的 AI 助手面板，可以方便地进行各种 AI 操作。

#### Acceptance Criteria

1. THE Frontend SHALL 提供统一的 AI 助手面板组件（AIAssistantPanel）
2. THE AIAssistantPanel SHALL 支持四种模式切换：任务创建、任务分析、任务修改、项目规划
3. WHEN 用户在项目详情页时，THE Frontend SHALL 显示"AI 分析"按钮，点击后打开任务分析模式
4. WHEN 用户在任务详情抽屉时，THE Frontend SHALL 显示"AI 修改"按钮，点击后打开任务修改模式
5. THE AIAssistantPanel SHALL 显示对话历史，包含用户消息和 AI 回复
6. THE AIAssistantPanel SHALL 提供消息输入框和发送按钮
7. WHEN AI 返回可执行操作时，THE AIAssistantPanel SHALL 显示操作按钮（如"应用修改"、"创建任务"）
8. THE AIAssistantPanel SHALL 显示加载状态，当 AI 正在思考时显示加载动画
9. THE AIAssistantPanel SHALL 支持查看历史对话列表，用户可以恢复之前的对话

### Requirement 7: API 接口设计

**User Story:** 作为开发者，我需要清晰的 API 接口来支持 AI 对话功能。

#### Acceptance Criteria

1. THE Backend SHALL 提供 POST /api/v1/conversations 接口，用于创建新对话
2. THE Backend SHALL 提供 POST /api/v1/conversations/{id}/messages 接口，用于发送消息
3. THE Backend SHALL 提供 GET /api/v1/conversations 接口，用于获取对话列表
4. THE Backend SHALL 提供 GET /api/v1/conversations/{id} 接口，用于获取对话详情
5. THE Backend SHALL 提供 POST /api/v1/conversations/{id}/analyze 接口，用于任务分析
6. THE Backend SHALL 提供 POST /api/v1/conversations/{id}/modify 接口，用于任务修改
7. THE Backend SHALL 提供 POST /api/v1/conversations/{id}/plan 接口，用于项目规划
8. THE Backend SHALL 提供 DELETE /api/v1/conversations/{id} 接口，用于删除对话
9. WHEN API 调用失败时，THE Backend SHALL 返回标准的错误响应，包含错误码和错误信息

### Requirement 8: 错误处理和用户反馈

**User Story:** 作为用户，当 AI 操作失败时，我希望看到清晰的错误提示和解决建议。

#### Acceptance Criteria

1. WHEN LLM API 调用超时时，THE AI_Conversation_Service SHALL 返回友好的超时提示
2. WHEN LLM API 返回 401/403 错误时，THE AI_Conversation_Service SHALL 提示用户检查 API Key 配置
3. WHEN LLM API 返回 429 错误时，THE AI_Conversation_Service SHALL 提示用户稍后重试
4. WHEN 任务修改操作失败时，THE Task_Modifier SHALL 返回具体的失败原因和建议
5. WHEN AI 无法理解用户意图时，THE AI_Conversation_Service SHALL 请求用户提供更多信息
6. THE Frontend SHALL 在操作成功时显示成功提示，包含操作结果摘要
7. THE Frontend SHALL 在操作失败时显示错误提示，包含错误原因和解决建议

### Requirement 9: 性能和资源管理

**User Story:** 作为系统管理员，我希望 AI 对话功能不会过度消耗系统资源。

#### Acceptance Criteria

1. THE AI_Conversation_Service SHALL 限制每个用户同时进行的对话数量不超过 10 个
2. THE Database SHALL 自动清理 30 天前的对话历史记录
3. THE AI_Conversation_Service SHALL 实现 LLM API 调用的速率限制，每个用户每分钟不超过 20 次调用
4. WHEN 对话上下文超过 4000 tokens 时，THE AI_Conversation_Service SHALL 自动压缩对话历史
5. THE Backend SHALL 为 LLM API 调用设置 60 秒超时
6. THE AI_Conversation_Service SHALL 缓存常见的分析结果，避免重复调用 LLM API
7. THE Database SHALL 为对话历史表设置合理的存储限制，单条对话记录不超过 100KB

### Requirement 10: 安全和权限控制

**User Story:** 作为系统管理员，我希望确保用户只能访问自己的对话历史和项目数据。

#### Acceptance Criteria

1. THE Backend SHALL 验证用户身份，确保用户只能访问自己创建的对话
2. WHEN 用户请求项目相关的对话时，THE Backend SHALL 验证用户对该项目的访问权限
3. THE Backend SHALL 在对话上下文中只包含用户有权访问的任务数据
4. THE Database SHALL 加密存储敏感的对话内容（如包含密码、API Key 的消息）
5. THE Backend SHALL 记录所有 AI 操作的审计日志，包含用户 ID、操作类型、时间戳
6. WHEN 用户删除项目时，THE Backend SHALL 同时删除相关的对话历史
7. THE Backend SHALL 限制对话历史的导出功能，只允许用户导出自己的对话
