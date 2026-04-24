# 需求文档 - 钉钉智能助手

## 简介

钉钉智能助手是 TaskTree 系统的双向交互增强功能，实现用户通过钉钉自然语言反馈任务进度，AI 自动理解并更新任务状态的完整闭环。该功能基于现有的钉钉推送服务、LLM 服务和 AI 对话记忆能力，新增消息回调接收、进度智能解析和任务自动更新能力。

## 术语表

- **DingtalkCallbackService**: 钉钉消息回调处理服务
- **ProgressParserService**: 进度解析服务，使用 LLM 理解用户自然语言
- **TaskMatcherService**: 任务匹配服务，将用户描述映射到具体任务
- **DingtalkUserMapping**: 钉钉用户身份映射表
- **ProgressFeedback**: 进度反馈记录表
- **System**: TaskTree 后端系统
- **User**: 通过钉钉发送消息的用户
- **LLM**: 大语言模型服务（Minimax/OpenAI/Anthropic）
- **Webhook**: 钉钉机器人回调地址

## 需求

### 需求 1: 钉钉消息回调接收

**用户故事:** 作为系统管理员，我希望系统能够接收钉钉用户发送的消息，以便实现双向交互。

#### 验收标准

1. WHEN 钉钉用户向机器人发送消息，THE System SHALL 接收消息回调请求
2. WHEN 接收到回调请求，THE System SHALL 验证钉钉签名的有效性
3. IF 签名验证失败，THEN THE System SHALL 返回 401 错误并记录安全日志
4. WHEN 签名验证成功，THE System SHALL 提取消息内容、发送者 ID 和时间戳
5. THE System SHALL 在 200 毫秒内响应钉钉回调请求
6. WHEN 处理消息时发生错误，THE System SHALL 返回友好的错误提示给用户

### 需求 2: 用户身份映射

**用户故事:** 作为用户，我希望绑定我的钉钉账号，以便系统识别我的身份并更新我的任务。

#### 验收标准

1. THE System SHALL 提供钉钉账号绑定接口
2. WHEN 用户首次通过钉钉发送消息，THE System SHALL 提示用户完成身份绑定
3. THE System SHALL 存储钉钉 userId 与系统用户 ID 的映射关系
4. WHEN 接收到钉钉消息，THE System SHALL 根据 userId 查找对应的系统用户
5. IF 用户未绑定，THEN THE System SHALL 返回绑定引导消息
6. THE System SHALL 支持用户解除钉钉账号绑定
7. THE System SHALL 确保一个钉钉账号只能绑定一个系统用户

### 需求 3: AI 进度解析

**用户故事:** 作为用户，我希望用自然语言描述任务进度，系统能够自动理解我的意图。

#### 验收标准

1. WHEN 用户发送进度反馈消息，THE ProgressParserService SHALL 调用 LLM 解析消息内容
2. THE ProgressParserService SHALL 识别进度类型（已完成、进行中、遇到问题、请求延期、查询状态）
3. THE ProgressParserService SHALL 提取任务关键词（任务名称、任务描述片段）
4. THE ProgressParserService SHALL 提取进度数值（百分比、剩余时间）
5. THE ProgressParserService SHALL 提取问题描述（如果用户报告问题）
6. THE ProgressParserService SHALL 返回结构化的解析结果（JSON 格式）
7. WHEN LLM 解析失败，THE System SHALL 使用规则引擎作为降级方案
8. THE ProgressParserService SHALL 在 3 秒内完成解析

### 需求 4: 任务智能匹配

**用户故事:** 作为用户，我希望系统能够根据我的描述自动找到对应的任务，而不需要输入任务 ID。

#### 验收标准

1. WHEN 解析出任务关键词，THE TaskMatcherService SHALL 在用户的任务列表中搜索匹配任务
2. THE TaskMatcherService SHALL 优先匹配任务名称完全相同的任务
3. THE TaskMatcherService SHALL 支持模糊匹配（任务名称包含关键词）
4. THE TaskMatcherService SHALL 优先匹配状态为"进行中"或"待处理"的任务
5. THE TaskMatcherService SHALL 优先匹配最近更新的任务
6. WHEN 找到多个匹配任务，THE System SHALL 返回任务列表供用户选择
7. WHEN 未找到匹配任务，THE System SHALL 提示用户并建议创建新任务
8. THE TaskMatcherService SHALL 在 500 毫秒内完成匹配

### 需求 5: 任务自动更新

**用户故事:** 作为用户，我希望系统根据我的反馈自动更新任务状态和进度，减少手动操作。

#### 验收标准

1. WHEN 用户反馈任务已完成，THE System SHALL 更新任务状态为"已完成"
2. WHEN 用户反馈任务进行中，THE System SHALL 更新任务状态为"进行中"
3. WHEN 用户提供进度百分比，THE System SHALL 更新任务进度字段
4. WHEN 用户报告问题，THE System SHALL 在任务描述中追加问题记录
5. WHEN 用户请求延期，THE System SHALL 调整任务截止日期
6. THE System SHALL 记录每次更新的来源为"钉钉反馈"
7. THE System SHALL 在操作日志中记录所有自动更新操作
8. WHEN 任务更新成功，THE System SHALL 通过钉钉回复确认消息

### 需求 6: 智能交互增强

**用户故事:** 作为用户，我希望系统能够提供智能建议和多轮对话，帮助我更好地管理任务。

#### 验收标准

1. WHEN 用户查询今日任务，THE System SHALL 返回当天截止或需要关注的任务列表
2. WHEN 用户查询项目进度，THE System SHALL 返回项目统计信息（完成率、剩余任务数）
3. WHEN 任务即将逾期，THE System SHALL 在回复中提醒用户
4. WHEN 用户报告问题，THE System SHALL 提供智能建议（延期、求助、调整优先级）
5. THE System SHALL 支持多轮对话（追问任务细节、确认操作）
6. THE System SHALL 使用 AIConversation 表存储对话历史
7. THE System SHALL 在回复中使用 Markdown 格式提升可读性
8. WHEN 用户输入不明确，THE System SHALL 请求用户澄清

### 需求 7: 安全性保障

**用户故事:** 作为系统管理员，我希望确保钉钉回调接口的安全性，防止恶意调用和数据泄露。

#### 验收标准

1. THE System SHALL 验证所有钉钉回调请求的签名
2. THE System SHALL 验证请求时间戳，拒绝超过 5 分钟的请求
3. THE System SHALL 确保用户只能更新自己负责的任务
4. THE System SHALL 记录所有回调请求的安全日志
5. THE System SHALL 对钉钉 secret 进行加密存储
6. THE System SHALL 限制单个用户的请求频率（每分钟最多 10 次）
7. IF 检测到异常请求模式，THEN THE System SHALL 临时封禁该用户
8. THE System SHALL 不在日志中记录敏感信息（API Key、用户密码）

### 需求 8: 数据模型扩展

**用户故事:** 作为开发者，我需要新的数据表来支持钉钉双向交互功能。

#### 验收标准

1. THE System SHALL 创建 DingtalkUserMapping 表存储用户身份映射
2. THE DingtalkUserMapping 表 SHALL 包含字段：id、user_id、dingtalk_user_id、dingtalk_name、bound_at、updated_at
3. THE System SHALL 创建 ProgressFeedback 表存储进度反馈记录
4. THE ProgressFeedback 表 SHALL 包含字段：id、user_id、task_id、message_content、parsed_result、feedback_type、created_at
5. THE System SHALL 在 UserNotificationSettings 表中新增字段：dingtalk_bot_webhook、dingtalk_bot_secret
6. THE System SHALL 确保 dingtalk_user_id 字段唯一
7. THE System SHALL 为所有外键字段创建索引
8. THE System SHALL 支持级联删除（用户删除时清理相关数据）

### 需求 9: API 接口设计

**用户故事:** 作为前端开发者，我需要清晰的 API 接口来实现钉钉账号绑定和反馈记录查询。

#### 验收标准

1. THE System SHALL 提供 POST /api/v1/dingtalk/callback 接口接收钉钉消息
2. THE System SHALL 提供 POST /api/v1/dingtalk/bind 接口绑定钉钉账号
3. THE System SHALL 提供 DELETE /api/v1/dingtalk/unbind 接口解除绑定
4. THE System SHALL 提供 GET /api/v1/dingtalk/binding 接口查询绑定状态
5. THE System SHALL 提供 GET /api/v1/progress-feedback 接口查询进度反馈历史
6. THE System SHALL 提供 POST /api/v1/dingtalk/test-message 接口测试钉钉消息发送
7. THE System SHALL 为所有接口提供 OpenAPI 文档
8. THE System SHALL 返回标准的 JSON 响应格式

### 需求 10: 前端用户界面

**用户故事:** 作为用户，我希望在前端界面中管理钉钉绑定和查看反馈历史。

#### 验收标准

1. THE System SHALL 在用户设置页面提供钉钉账号绑定入口
2. THE System SHALL 显示当前绑定状态（已绑定/未绑定）
3. THE System SHALL 提供绑定二维码或绑定码
4. THE System SHALL 在任务详情页显示钉钉反馈记录
5. THE System SHALL 显示每条反馈的时间、内容和解析结果
6. THE System SHALL 在项目设置页提供钉钉机器人配置入口
7. THE System SHALL 提供测试消息发送功能
8. THE System SHALL 显示绑定和反馈的操作历史

### 需求 11: 错误处理和降级

**用户故事:** 作为系统管理员，我希望系统在 LLM 服务不可用时仍能提供基础功能。

#### 验收标准

1. WHEN LLM 服务不可用，THE System SHALL 使用规则引擎解析进度
2. THE System SHALL 识别常见关键词（完成、进行中、问题、延期）
3. THE System SHALL 提取百分比数字（如"50%"、"一半"）
4. WHEN 规则引擎无法解析，THE System SHALL 提示用户使用标准格式
5. THE System SHALL 记录降级事件到日志
6. THE System SHALL 在 LLM 服务恢复后自动切换回 AI 解析
7. THE System SHALL 提供降级状态监控接口
8. THE System SHALL 在降级模式下保持 95% 的基础功能可用

### 需求 12: 性能和可扩展性

**用户故事:** 作为系统架构师，我希望系统能够支持大量并发用户和消息处理。

#### 验收标准

1. THE System SHALL 在 200 毫秒内响应钉钉回调请求
2. THE System SHALL 支持每秒处理 100 个并发消息
3. THE System SHALL 使用异步任务队列处理 LLM 调用
4. THE System SHALL 缓存用户身份映射关系（5 分钟）
5. THE System SHALL 缓存用户任务列表（1 分钟）
6. THE System SHALL 限制单次查询返回的任务数量（最多 50 个）
7. THE System SHALL 使用数据库连接池管理数据库连接
8. THE System SHALL 记录所有接口的响应时间到监控系统

### 需求 13: 消息解析器和打印器

**用户故事:** 作为开发者，我需要可靠的消息解析和格式化能力，确保数据的一致性。

#### 验收标准

1. WHEN 接收到钉钉消息，THE MessageParser SHALL 解析消息为结构化对象
2. THE MessageParser SHALL 支持文本消息、Markdown 消息和富文本消息
3. THE MessageParser SHALL 提取 @提及的用户列表
4. THE MessageParser SHALL 提取消息中的链接和附件
5. THE MessagePrinter SHALL 将结构化对象格式化为钉钉 Markdown 格式
6. THE MessagePrinter SHALL 支持任务列表、进度条和状态标签的格式化
7. FOR ALL 有效的消息对象，解析后打印再解析 SHALL 产生等价的对象（round-trip property）
8. WHEN 消息格式无效，THE MessageParser SHALL 返回描述性错误

### 需求 14: 集成测试和监控

**用户故事:** 作为 QA 工程师，我需要完整的测试覆盖和监控能力，确保功能稳定性。

#### 验收标准

1. THE System SHALL 提供钉钉回调接口的集成测试
2. THE System SHALL 提供进度解析服务的单元测试
3. THE System SHALL 提供任务匹配算法的单元测试
4. THE System SHALL 记录所有钉钉消息处理的成功率
5. THE System SHALL 记录 LLM 解析的准确率
6. THE System SHALL 记录任务匹配的成功率
7. THE System SHALL 提供健康检查接口（/health/dingtalk）
8. THE System SHALL 在监控面板显示关键指标（消息量、成功率、响应时间）

## 非功能性需求

### 性能要求

- 钉钉回调响应时间 < 200ms
- LLM 解析时间 < 3s
- 任务匹配时间 < 500ms
- 支持 100 并发用户

### 可用性要求

- 系统可用性 > 99.5%
- LLM 服务降级后基础功能可用性 > 95%
- 错误消息清晰易懂

### 安全性要求

- 所有回调请求必须验证签名
- 用户只能操作自己的任务
- 敏感信息加密存储
- 请求频率限制

### 兼容性要求

- 支持钉钉企业内部机器人
- 支持钉钉群机器人
- 兼容现有的 LLM 服务（Minimax/OpenAI/Anthropic）
- 兼容现有的任务管理 API

## 依赖关系

### 现有系统能力（可复用）

- ✅ LLM 服务（llm_service.py）
- ✅ 钉钉推送服务（dingtalk_service.py）
- ✅ AI 对话记忆（ai_conversation_service.py）
- ✅ 任务 CRUD API（tasks.py）
- ✅ 用户认证和权限（auth.py）

### 新增能力

- 🆕 钉钉消息回调接口
- 🆕 进度解析服务（ProgressParserService）
- 🆕 任务匹配服务（TaskMatcherService）
- 🆕 用户身份映射（DingtalkUserMapping 表）
- 🆕 进度反馈记录（ProgressFeedback 表）

## 实现优先级

### P0（核心功能）

- 钉钉消息回调接收
- 用户身份映射
- AI 进度解析
- 任务自动更新

### P1（重要功能）

- 任务智能匹配
- 安全性保障
- 错误处理和降级

### P2（增强功能）

- 智能交互增强
- 前端用户界面
- 性能优化

### P3（监控和测试）

- 集成测试
- 监控面板
- 性能指标

## 风险和挑战

### 技术风险

1. **LLM 解析准确率**: 自然语言理解可能不准确
   - 缓解措施: 提供规则引擎降级方案，支持用户确认

2. **任务匹配歧义**: 多个任务名称相似
   - 缓解措施: 返回候选列表供用户选择

3. **钉钉 API 限制**: 回调超时、频率限制
   - 缓解措施: 异步处理、队列缓冲

### 业务风险

1. **用户学习成本**: 用户不熟悉自然语言交互
   - 缓解措施: 提供使用示例和帮助文档

2. **数据一致性**: 自动更新可能与手动操作冲突
   - 缓解措施: 记录操作来源，支持撤销

## 后续迭代方向

1. 支持语音消息识别
2. 支持图片识别（截图中的任务信息）
3. 支持团队协作（@同事分配任务）
4. 支持自定义命令（快捷指令）
5. 支持多语言（英文、日文）
