# 设计文档 - 钉钉智能助手

## 概述

钉钉智能助手是 TaskTree 系统的双向交互增强功能，实现用户通过钉钉自然语言反馈任务进度，AI 自动理解并更新任务状态的完整闭环。

### 核心功能流程

```
用户在钉钉发送消息
    ↓
系统接收回调请求 (验证签名)
    ↓
用户身份映射 (钉钉 ID → 系统用户)
    ↓
AI 进度解析 (LLM 理解自然语言)
    ↓
任务智能匹配 (关键词 → 具体任务)
    ↓
任务自动更新 (状态、进度、截止日期)
    ↓
钉钉回复确认 (Markdown 格式)
```

### 设计原则

1. **异步优先**: 所有 LLM 调用使用异步任务队列，保证 200ms 内响应钉钉回调
2. **降级可用**: LLM 不可用时使用规则引擎，保证基础功能可用
3. **安全第一**: 所有回调请求验证签名，用户只能操作自己的任务
4. **用户确认**: 自动更新前请求用户确认，防止误操作
5. **完整记录**: 所有操作记录来源和时间戳，支持审计和撤销

## 架构设计

### 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      钉钉用户                                │
└────────────────────────┬────────────────────────────────────┘
                         │ 发送消息
                         ↓
┌─────────────────────────────────────────────────────────────┐
│              钉钉回调接口 (DingtalkCallbackAPI)              │
│  - 验证签名                                                  │
│  - 提取消息内容、发送者、时间戳                              │
│  - 200ms 内响应                                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│           异步任务队列 (Celery/RQ)                           │
│  - 解耦回调处理和业务逻辑                                    │
│  - 支持重试和错误处理                                        │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ↓                ↓                ↓
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ 用户身份映射  │ │ AI 进度解析   │ │ 任务智能匹配  │
│ (Mapping)    │ │ (Parser)     │ │ (Matcher)    │
└──────────────┘ └──────────────┘ └──────────────┘
        │                │                │
        └────────────────┼────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│           任务自动更新 (TaskUpdater)                         │
│  - 更新任务状态、进度、截止日期                              │
│  - 记录操作日志                                              │
│  - 触发通知                                                  │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ↓                ↓                ↓
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ 数据库更新    │ │ 钉钉回复     │ │ 操作日志     │
│ (Task)       │ │ (DingtalkMsg)│ │ (AuditLog)   │
└──────────────┘ └──────────────┘ └──────────────┘
```

### 核心模块

#### 1. DingtalkCallbackAPI (钉钉回调接口)

**职责**:
- 接收钉钉消息回调
- 验证签名和时间戳
- 快速响应 (< 200ms)
- 将消息放入异步队列

**关键特性**:
- 签名验证: HMAC-SHA256
- 时间戳验证: 拒绝超过 5 分钟的请求
- 频率限制: 每个用户每分钟最多 10 次
- 安全日志: 记录所有验证失败的请求

#### 2. ProgressParserService (进度解析服务)

**职责**:
- 调用 LLM 解析自然语言
- 提取进度类型、关键词、数值、问题描述
- 降级到规则引擎

**进度类型**:
- `completed`: 任务已完成
- `in_progress`: 任务进行中
- `problem`: 遇到问题
- `extend`: 请求延期
- `query`: 查询状态

**解析结果结构**:
```json
{
  "progress_type": "in_progress",
  "confidence": 0.95,
  "keywords": ["任务名称", "描述片段"],
  "progress_value": 50,
  "problem_description": "遇到的问题",
  "extend_days": 3,
  "raw_message": "原始消息"
}
```

#### 3. TaskMatcherService (任务匹配服务)

**职责**:
- 根据关键词在用户任务列表中搜索
- 返回匹配的任务列表
- 支持模糊匹配和排序

**匹配策略**:
1. 完全匹配任务名称 (权重: 100)
2. 任务名称包含关键词 (权重: 80)
3. 任务描述包含关键词 (权重: 60)
4. 优先匹配"进行中"或"待处理"状态 (权重: +20)
5. 优先匹配最近更新的任务 (权重: +10)

**返回结果**:
- 单个匹配: 直接返回任务
- 多个匹配: 返回候选列表供用户选择
- 无匹配: 提示用户并建议创建新任务

#### 4. TaskUpdaterService (任务更新服务)

**职责**:
- 根据解析结果更新任务
- 记录操作日志
- 触发通知

**更新规则**:
- `completed`: 状态 → "已完成"
- `in_progress`: 状态 → "进行中"
- `progress_value`: 进度字段 → 百分比
- `problem_description`: 追加到任务描述
- `extend_days`: 截止日期 → 延期 N 天

#### 5. MessageParserService (消息解析服务)

**职责**:
- 解析钉钉消息格式
- 支持文本、Markdown、富文本
- 提取 @提及、链接、附件

#### 6. MessagePrinterService (消息打印服务)

**职责**:
- 将结构化数据格式化为钉钉 Markdown
- 支持任务列表、进度条、状态标签

## 组件和接口

### 数据流接口

#### 1. 钉钉回调接口

```
POST /api/v1/dingtalk/callback

请求头:
  X-Dingtalk-Timestamp: 时间戳
  X-Dingtalk-Sign: 签名

请求体:
{
  "msgtype": "text",
  "text": {
    "content": "用户消息内容"
  },
  "senderId": "钉钉用户ID",
  "createAt": 1234567890000,
  "conversationId": "会话ID"
}

响应 (< 200ms):
{
  "code": 0,
  "message": "success"
}
```

#### 2. 用户绑定接口

```
POST /api/v1/dingtalk/bind

请求体:
{
  "dingtalk_user_id": "钉钉用户ID",
  "dingtalk_name": "钉钉昵称",
  "verification_code": "验证码"
}

响应:
{
  "code": 0,
  "message": "绑定成功",
  "data": {
    "user_id": 123,
    "dingtalk_user_id": "xxx",
    "bound_at": "2024-01-01T00:00:00Z"
  }
}
```

#### 3. 进度反馈查询接口

```
GET /api/v1/progress-feedback?task_id=123&limit=20

响应:
{
  "code": 0,
  "data": [
    {
      "id": 1,
      "user_id": 123,
      "task_id": 456,
      "message_content": "已完成",
      "parsed_result": {...},
      "feedback_type": "completed",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

### 服务接口

#### ProgressParserService

```python
class ProgressParserService:
    async def parse(self, message: str, user_context: dict) -> ParseResult:
        """
        解析进度消息
        
        Args:
            message: 用户消息
            user_context: 用户上下文 (任务列表等)
            
        Returns:
            ParseResult: 解析结果
        """
        
    async def parse_with_fallback(self, message: str) -> ParseResult:
        """
        带降级的解析 (LLM → 规则引擎)
        """
```

#### TaskMatcherService

```python
class TaskMatcherService:
    async def match(
        self,
        keywords: list,
        user_id: int,
        limit: int = 5
    ) -> List[Task]:
        """
        匹配任务
        
        Args:
            keywords: 关键词列表
            user_id: 用户ID
            limit: 返回最多任务数
            
        Returns:
            匹配的任务列表
        """
```

#### TaskUpdaterService

```python
class TaskUpdaterService:
    async def update_from_feedback(
        self,
        task_id: int,
        parse_result: ParseResult,
        user_id: int
    ) -> Task:
        """
        根据反馈更新任务
        
        Args:
            task_id: 任务ID
            parse_result: 解析结果
            user_id: 用户ID
            
        Returns:
            更新后的任务
        """
```

## 数据模型

### 新增表

#### 1. DingtalkUserMapping (钉钉用户映射表)

```sql
CREATE TABLE dingtalk_user_mapping (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL UNIQUE,
    dingtalk_user_id VARCHAR(255) NOT NULL UNIQUE,
    dingtalk_name VARCHAR(255),
    bound_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
    INDEX idx_dingtalk_user_id (dingtalk_user_id),
    INDEX idx_user_id (user_id)
);
```

**字段说明**:
- `id`: 主键
- `user_id`: 系统用户ID (唯一)
- `dingtalk_user_id`: 钉钉用户ID (唯一)
- `dingtalk_name`: 钉钉昵称
- `bound_at`: 绑定时间
- `updated_at`: 更新时间

#### 2. ProgressFeedback (进度反馈表)

```sql
CREATE TABLE progress_feedback (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    task_id INT NOT NULL,
    message_content TEXT NOT NULL,
    parsed_result JSON,
    feedback_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES task(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_task_id (task_id),
    INDEX idx_created_at (created_at)
);
```

**字段说明**:
- `id`: 主键
- `user_id`: 用户ID
- `task_id`: 任务ID
- `message_content`: 原始消息内容
- `parsed_result`: 解析结果 (JSON)
- `feedback_type`: 反馈类型 (completed/in_progress/problem/extend/query)
- `created_at`: 创建时间

#### 3. UserNotificationSettings 扩展

在现有 `user_notification_settings` 表中新增字段:

```sql
ALTER TABLE user_notification_settings ADD COLUMN (
    dingtalk_bot_webhook VARCHAR(500),
    dingtalk_bot_secret VARCHAR(255),
    dingtalk_enabled BOOLEAN DEFAULT FALSE
);
```

### 数据模型关系

```
User (1) ──── (1) DingtalkUserMapping
  │
  ├──── (N) ProgressFeedback
  │
  └──── (1) UserNotificationSettings
        └── dingtalk_bot_webhook
        └── dingtalk_bot_secret
        └── dingtalk_enabled

Task (1) ──── (N) ProgressFeedback
```

## 错误处理

### 回调处理错误

| 错误类型 | HTTP 状态 | 处理方式 |
|---------|---------|--------|
| 签名验证失败 | 401 | 记录安全日志，拒绝请求 |
| 时间戳过期 | 401 | 记录安全日志，拒绝请求 |
| 用户未绑定 | 400 | 返回绑定引导消息 |
| 消息格式错误 | 400 | 返回错误提示 |
| 内部错误 | 500 | 返回通用错误，记录详细日志 |

### LLM 解析错误

| 错误类型 | 处理方式 |
|---------|--------|
| API 超时 | 使用规则引擎降级 |
| API 限流 | 重试 + 指数退避 |
| API 认证失败 | 记录错误，使用规则引擎 |
| 解析失败 | 请求用户澄清 |

### 任务匹配错误

| 错误类型 | 处理方式 |
|---------|--------|
| 无匹配任务 | 提示用户，建议创建新任务 |
| 多个匹配 | 返回候选列表，请求用户选择 |
| 任务不存在 | 返回错误提示 |

## 测试策略

### 单元测试

1. **ProgressParserService**
   - 测试 LLM 解析各种进度类型
   - 测试规则引擎降级
   - 测试关键词提取
   - 测试数值提取

2. **TaskMatcherService**
   - 测试完全匹配
   - 测试模糊匹配
   - 测试排序算法
   - 测试边界情况

3. **MessageParserService**
   - 测试文本消息解析
   - 测试 Markdown 消息解析
   - 测试 @提及提取
   - 测试链接提取

4. **MessagePrinterService**
   - 测试任务列表格式化
   - 测试进度条格式化
   - 测试状态标签格式化

### 集成测试

1. **钉钉回调流程**
   - 测试完整的消息处理流程
   - 测试签名验证
   - 测试异步处理
   - 测试错误恢复

2. **任务更新流程**
   - 测试任务状态更新
   - 测试进度更新
   - 测试截止日期调整
   - 测试操作日志记录

3. **用户绑定流程**
   - 测试绑定成功
   - 测试绑定冲突
   - 测试解除绑定

### 性能测试

1. **回调响应时间**: < 200ms
2. **LLM 解析时间**: < 3s
3. **任务匹配时间**: < 500ms
4. **并发处理**: 支持 100 并发用户

### 安全测试

1. **签名验证**: 测试无效签名被拒绝
2. **时间戳验证**: 测试过期请求被拒绝
3. **权限验证**: 测试用户只能操作自己的任务
4. **频率限制**: 测试超过限制的请求被拒绝

## 实现计划

### 第一阶段 (P0 - 核心功能)

1. 创建数据模型 (DingtalkUserMapping, ProgressFeedback)
2. 实现钉钉回调接口 (签名验证、快速响应)
3. 实现用户身份映射 (绑定、查询、解除)
4. 实现 ProgressParserService (LLM 调用)
5. 实现 TaskMatcherService (任务搜索)
6. 实现 TaskUpdaterService (任务更新)

### 第二阶段 (P1 - 重要功能)

1. 实现规则引擎降级方案
2. 实现安全性保障 (频率限制、安全日志)
3. 实现错误处理和恢复
4. 实现操作日志记录

### 第三阶段 (P2 - 增强功能)

1. 实现智能交互增强 (多轮对话)
2. 实现前端用户界面
3. 实现性能优化 (缓存、异步处理)

### 第四阶段 (P3 - 监控和测试)

1. 实现集成测试
2. 实现监控面板
3. 实现性能指标收集

## 依赖关系

### 现有系统能力

- ✅ LLMService: 用于 AI 进度解析
- ✅ DingtalkService: 用于发送钉钉消息
- ✅ AIConversationService: 用于存储对话历史
- ✅ Task CRUD API: 用于任务更新
- ✅ User 认证: 用于权限验证

### 新增能力

- 🆕 DingtalkCallbackAPI: 接收钉钉消息
- 🆕 ProgressParserService: 解析进度
- 🆕 TaskMatcherService: 匹配任务
- 🆕 MessageParserService: 解析消息
- 🆕 MessagePrinterService: 格式化消息
- 🆕 DingtalkUserMapping 表: 用户映射
- 🆕 ProgressFeedback 表: 反馈记录

## 风险和缓解

### 技术风险

1. **LLM 解析准确率低**
   - 缓解: 提供规则引擎降级，支持用户确认

2. **任务匹配歧义**
   - 缓解: 返回候选列表，请求用户选择

3. **钉钉 API 限制**
   - 缓解: 异步处理，队列缓冲，重试机制

### 业务风险

1. **自动更新误操作**
   - 缓解: 记录操作来源，支持撤销，提供操作日志

2. **用户学习成本**
   - 缓解: 提供使用示例，帮助文档，错误提示



## 正确性属性

*属性是系统应该在所有有效执行中保持为真的特征或行为——本质上是关于系统应该做什么的形式化陈述。属性充当人类可读的规范和机器可验证的正确性保证之间的桥梁。*

### 属性反思和冗余消除

在初始分析中，我们识别了以下可测试的属性：

**签名验证相关**:
- 属性 1: 有效签名被接受
- 属性 2: 无效签名被拒绝
- 属性 3: 过期时间戳被拒绝

这三个属性可以合并为一个更全面的属性：**签名和时间戳验证**

**消息解析相关**:
- 属性 4: 消息字段提取
- 属性 5: 进度类型识别
- 属性 6: 关键词提取
- 属性 7: 数值提取
- 属性 8: 问题描述提取

这些属性都测试解析逻辑的不同方面，可以合并为：**消息解析的完整性**

**任务匹配相关**:
- 属性 9: 完全匹配优先级
- 属性 10: 模糊匹配支持
- 属性 11: 状态优先级
- 属性 12: 时间优先级

这些属性都测试匹配排序逻辑，可以合并为：**任务匹配排序的一致性**

**任务更新相关**:
- 属性 13: 状态转换有效性
- 属性 14: 进度更新有效性
- 属性 15: 日期调整有效性

这些属性都测试状态转换，可以合并为：**任务状态转换的有效性**

**消息格式化相关**:
- 属性 16: Markdown 格式化
- 属性 17: Round-trip 属性

这两个属性可以合并为：**消息格式化的 Round-trip 属性**

### 最终属性列表

#### 属性 1: 签名和时间戳验证

*对于任何钉钉回调请求，如果签名有效且时间戳在 5 分钟内，系统应该接受请求；否则应该拒绝请求。*

**验证需求**: 需求 1.2, 7.1, 7.2

#### 属性 2: 消息字段提取的完整性

*对于任何有效的钉钉消息，解析后应该能够提取消息内容、发送者 ID 和时间戳，且提取的值应该与原始消息一致。*

**验证需求**: 需求 1.4, 13.1

#### 属性 3: 进度类型识别的准确性

*对于任何包含进度信息的消息，解析器应该能够识别进度类型（已完成、进行中、遇到问题、请求延期、查询状态）中的至少一个。*

**验证需求**: 需求 3.2

#### 属性 4: 关键词和数值提取

*对于任何包含任务关键词或数值的消息，解析器应该能够正确提取关键词列表和数值（百分比、天数）。*

**验证需求**: 需求 3.3, 3.4, 3.5, 11.2, 11.3

#### 属性 5: 解析结果的有效性

*对于任何消息，解析结果应该总是返回有效的 JSON 格式，包含必需的字段（progress_type, confidence, keywords）。*

**验证需求**: 需求 3.6, 9.8

#### 属性 6: 用户身份映射的唯一性

*对于任何钉钉用户 ID，系统中最多只能存在一个映射到系统用户的记录。*

**验证需求**: 需求 2.7, 8.6

#### 属性 7: 用户身份查询的一致性

*对于任何已绑定的钉钉用户 ID，查询应该总是返回相同的系统用户 ID。*

**验证需求**: 需求 2.4

#### 属性 8: 任务匹配排序的一致性

*对于任何任务列表和关键词，匹配结果应该按照优先级排序：完全匹配 > 模糊匹配，进行中/待处理 > 其他状态，最近更新 > 较早更新。*

**验证需求**: 需求 4.1, 4.2, 4.3, 4.4, 4.5

#### 属性 9: 任务状态转换的有效性

*对于任何任务，状态转换应该遵循有效的状态机：待处理 → 进行中 → 已完成，且进度值应该在 0-100% 之间。*

**验证需求**: 需求 5.1, 5.2, 5.3

#### 属性 10: 任务元数据更新的原子性

*对于任何任务更新操作，所有相关字段（状态、进度、截止日期、描述）应该在同一个事务中更新，或者全部成功或全部失败。*

**验证需求**: 需求 5.4, 5.5

#### 属性 11: 频率限制的强制性

*对于任何用户，在一分钟内超过 10 次请求应该被拒绝。*

**验证需求**: 需求 7.6

#### 属性 12: 权限验证的正确性

*对于任何任务更新请求，系统应该验证请求用户是否有权限修改该任务（任务所有者或项目成员）。*

**验证需求**: 需求 7.3

#### 属性 13: 消息格式化的 Round-trip 属性

*对于任何有效的结构化消息对象，解析 → 打印 → 解析应该产生等价的对象。*

**验证需求**: 需求 13.7

#### 属性 14: 消息格式支持的完整性

*对于任何文本、Markdown 或富文本格式的消息，解析器应该能够正确处理，并提取 @提及、链接和附件。*

**验证需求**: 需求 13.2, 13.3, 13.4

#### 属性 15: 错误消息的描述性

*对于任何无效的消息格式，解析器应该返回包含具体错误原因的错误消息。*

**验证需求**: 需求 13.8

#### 属性 16: 规则引擎降级的准确性

*当 LLM 不可用时，规则引擎应该能够识别常见关键词（完成、进行中、问题、延期）和百分比数字，准确率不低于 80%。*

**验证需求**: 需求 11.1, 11.2, 11.3

#### 属性 17: 查询结果的限制

*对于任何任务查询，返回的任务数量应该不超过 50 个。*

**验证需求**: 需求 12.6

#### 属性 18: 级联删除的完整性

*当删除一个用户时，所有相关的 DingtalkUserMapping 和 ProgressFeedback 记录应该被自动删除。*

**验证需求**: 需求 8.8

#### 属性 19: 今日任务查询的准确性

*对于任何用户，查询今日任务应该返回所有截止日期为今天或已逾期的任务。*

**验证需求**: 需求 6.1

#### 属性 20: 项目统计的准确性

*对于任何项目，统计信息（完成率、剩余任务数）应该与实际任务状态一致。*

**验证需求**: 需求 6.2

## 测试策略

### 属性测试配置

所有属性测试应该满足以下要求：

1. **最少迭代次数**: 100 次（确保充分的输入覆盖）
2. **测试标签格式**: `Feature: dingtalk-smart-assistant, Property {number}: {property_text}`
3. **测试框架**: 使用 Python 的 Hypothesis 库进行属性测试
4. **生成器策略**: 为每个属性定义合适的输入生成器

### 单元测试

#### ProgressParserService 单元测试

```python
# 测试 LLM 解析各种进度类型
def test_parse_completed_status()
def test_parse_in_progress_status()
def test_parse_problem_status()
def test_parse_extend_status()
def test_parse_query_status()

# 测试关键词提取
def test_extract_keywords()
def test_extract_progress_value()
def test_extract_problem_description()

# 测试规则引擎降级
def test_fallback_to_rule_engine()
def test_rule_engine_keyword_recognition()
def test_rule_engine_percentage_extraction()
```

#### TaskMatcherService 单元测试

```python
# 测试匹配算法
def test_exact_match_priority()
def test_fuzzy_match_support()
def test_status_priority()
def test_recency_priority()
def test_match_sorting()

# 测试边界情况
def test_no_match_found()
def test_multiple_matches()
def test_empty_task_list()
```

#### MessageParserService 单元测试

```python
# 测试消息解析
def test_parse_text_message()
def test_parse_markdown_message()
def test_parse_rich_text_message()

# 测试提取功能
def test_extract_mentions()
def test_extract_links()
def test_extract_attachments()
```

#### MessagePrinterService 单元测试

```python
# 测试格式化
def test_format_task_list()
def test_format_progress_bar()
def test_format_status_tags()
def test_markdown_validity()
```

### 集成测试

#### 钉钉回调流程集成测试

```python
# 测试完整流程
async def test_dingtalk_callback_flow()
async def test_signature_verification()
async def test_timestamp_validation()
async def test_async_processing()
async def test_error_recovery()
```

#### 任务更新流程集成测试

```python
# 测试任务更新
async def test_task_status_update()
async def test_task_progress_update()
async def test_task_deadline_adjustment()
async def test_operation_logging()
```

#### 用户绑定流程集成测试

```python
# 测试绑定流程
async def test_user_binding()
async def test_binding_conflict()
async def test_unbinding()
async def test_binding_query()
```

### 性能测试

1. **回调响应时间**: 验证 < 200ms
2. **LLM 解析时间**: 验证 < 3s
3. **任务匹配时间**: 验证 < 500ms
4. **并发处理**: 验证支持 100 并发用户

### 安全测试

1. **签名验证**: 验证无效签名被拒绝
2. **时间戳验证**: 验证过期请求被拒绝
3. **权限验证**: 验证用户只能操作自己的任务
4. **频率限制**: 验证超过限制的请求被拒绝



## API 接口详细设计

### 1. 钉钉回调接口

```
POST /api/v1/dingtalk/callback

请求头:
  X-Dingtalk-Timestamp: 1234567890000
  X-Dingtalk-Sign: base64_encoded_signature
  Content-Type: application/json

请求体:
{
  "msgtype": "text",
  "text": {
    "content": "已完成任务 A，进度 100%"
  },
  "senderId": "dingtalk_user_123",
  "createAt": 1234567890000,
  "conversationId": "conv_123"
}

响应 (< 200ms):
{
  "code": 0,
  "message": "success"
}

错误响应:
{
  "code": 401,
  "message": "签名验证失败"
}
```

### 2. 用户绑定接口

```
POST /api/v1/dingtalk/bind

请求头:
  Authorization: Bearer {token}
  Content-Type: application/json

请求体:
{
  "dingtalk_user_id": "dingtalk_user_123",
  "dingtalk_name": "张三",
  "verification_code": "123456"
}

响应:
{
  "code": 0,
  "message": "绑定成功",
  "data": {
    "user_id": 123,
    "dingtalk_user_id": "dingtalk_user_123",
    "dingtalk_name": "张三",
    "bound_at": "2024-01-01T00:00:00Z"
  }
}
```

### 3. 解除绑定接口

```
DELETE /api/v1/dingtalk/unbind

请求头:
  Authorization: Bearer {token}

响应:
{
  "code": 0,
  "message": "解除绑定成功"
}
```

### 4. 查询绑定状态接口

```
GET /api/v1/dingtalk/binding

请求头:
  Authorization: Bearer {token}

响应:
{
  "code": 0,
  "data": {
    "is_bound": true,
    "dingtalk_user_id": "dingtalk_user_123",
    "dingtalk_name": "张三",
    "bound_at": "2024-01-01T00:00:00Z"
  }
}
```

### 5. 进度反馈查询接口

```
GET /api/v1/progress-feedback?task_id=123&limit=20&offset=0

请求头:
  Authorization: Bearer {token}

响应:
{
  "code": 0,
  "data": [
    {
      "id": 1,
      "user_id": 123,
      "task_id": 456,
      "message_content": "已完成",
      "parsed_result": {
        "progress_type": "completed",
        "confidence": 0.95,
        "keywords": ["任务名称"],
        "progress_value": 100
      },
      "feedback_type": "completed",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 100,
  "limit": 20,
  "offset": 0
}
```

### 6. 测试消息发送接口

```
POST /api/v1/dingtalk/test-message

请求头:
  Authorization: Bearer {token}
  Content-Type: application/json

请求体:
{
  "message": "测试消息内容"
}

响应:
{
  "code": 0,
  "message": "消息发送成功",
  "data": {
    "message_id": "msg_123"
  }
}
```

### 7. 健康检查接口

```
GET /health/dingtalk

响应:
{
  "status": "healthy",
  "dingtalk_service": "ok",
  "llm_service": "ok",
  "database": "ok",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## 服务实现指南

### ProgressParserService 实现

```python
class ProgressParserService:
    def __init__(self, llm_service: LLMService, db: AsyncSession):
        self.llm_service = llm_service
        self.db = db
        self.rule_engine = RuleBasedParser()
    
    async def parse(self, message: str, user_context: dict) -> ParseResult:
        """使用 LLM 解析消息"""
        try:
            # 构建 LLM 提示词
            prompt = self._build_parse_prompt(message, user_context)
            
            # 调用 LLM
            response = await self.llm_service.chat(
                messages=[
                    {"role": "system", "content": "你是任务进度解析助手"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            # 解析 LLM 响应
            result = self._parse_llm_response(response)
            return result
            
        except Exception as e:
            # 降级到规则引擎
            return await self.parse_with_fallback(message)
    
    async def parse_with_fallback(self, message: str) -> ParseResult:
        """使用规则引擎降级解析"""
        return self.rule_engine.parse(message)
    
    def _build_parse_prompt(self, message: str, context: dict) -> str:
        """构建 LLM 提示词"""
        return f"""
        分析以下任务进度消息，返回 JSON 格式的结构化结果。
        
        消息: {message}
        
        用户任务列表:
        {self._format_task_list(context.get('tasks', []))}
        
        返回格式:
        {{
            "progress_type": "completed|in_progress|problem|extend|query",
            "confidence": 0.0-1.0,
            "keywords": ["关键词1", "关键词2"],
            "progress_value": 0-100,
            "problem_description": "问题描述或空字符串",
            "extend_days": 0,
            "raw_message": "{message}"
        }}
        """
```

### TaskMatcherService 实现

```python
class TaskMatcherService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def match(
        self,
        keywords: list,
        user_id: int,
        limit: int = 5
    ) -> List[Task]:
        """匹配任务"""
        # 获取用户的所有任务
        tasks = await self._get_user_tasks(user_id)
        
        # 计算每个任务的匹配分数
        scored_tasks = []
        for task in tasks:
            score = self._calculate_match_score(task, keywords)
            if score > 0:
                scored_tasks.append((task, score))
        
        # 按分数排序
        scored_tasks.sort(key=lambda x: x[1], reverse=True)
        
        # 返回前 limit 个任务
        return [task for task, score in scored_tasks[:limit]]
    
    def _calculate_match_score(self, task: Task, keywords: list) -> float:
        """计算匹配分数"""
        score = 0.0
        
        for keyword in keywords:
            # 完全匹配任务名称
            if task.name == keyword:
                score += 100
            # 任务名称包含关键词
            elif keyword in task.name:
                score += 80
            # 任务描述包含关键词
            elif keyword in (task.description or ""):
                score += 60
        
        # 优先匹配进行中或待处理的任务
        if task.status in ["in_progress", "pending"]:
            score += 20
        
        # 优先匹配最近更新的任务
        days_since_update = (datetime.now() - task.updated_at).days
        if days_since_update == 0:
            score += 10
        elif days_since_update <= 7:
            score += 5
        
        return score
```

### TaskUpdaterService 实现

```python
class TaskUpdaterService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def update_from_feedback(
        self,
        task_id: int,
        parse_result: ParseResult,
        user_id: int
    ) -> Task:
        """根据反馈更新任务"""
        # 获取任务
        task = await self._get_task(task_id, user_id)
        
        # 验证权限
        if not await self._check_permission(task, user_id):
            raise PermissionError("无权限修改此任务")
        
        # 根据进度类型更新
        if parse_result.progress_type == "completed":
            task.status = "completed"
            task.progress = 100
        
        elif parse_result.progress_type == "in_progress":
            task.status = "in_progress"
            if parse_result.progress_value:
                task.progress = parse_result.progress_value
        
        elif parse_result.progress_type == "problem":
            # 追加问题描述
            if parse_result.problem_description:
                task.description = f"{task.description}\n\n问题: {parse_result.problem_description}"
        
        elif parse_result.progress_type == "extend":
            # 调整截止日期
            if parse_result.extend_days:
                task.due_date = task.due_date + timedelta(days=parse_result.extend_days)
        
        # 记录操作来源
        task.updated_by_source = "dingtalk_feedback"
        task.updated_at = datetime.now(timezone.utc)
        
        # 保存
        await self.db.commit()
        await self.db.refresh(task)
        
        # 记录操作日志
        await self._log_operation(task_id, user_id, parse_result)
        
        return task
```

## 缓存策略

### 用户身份映射缓存

```python
class DingtalkUserMappingCache:
    def __init__(self, ttl: int = 300):  # 5 分钟
        self.cache = {}
        self.ttl = ttl
    
    async def get(self, dingtalk_user_id: str) -> Optional[int]:
        """获取缓存的用户 ID"""
        if dingtalk_user_id in self.cache:
            entry = self.cache[dingtalk_user_id]
            if time.time() - entry['timestamp'] < self.ttl:
                return entry['user_id']
            else:
                del self.cache[dingtalk_user_id]
        return None
    
    def set(self, dingtalk_user_id: str, user_id: int):
        """设置缓存"""
        self.cache[dingtalk_user_id] = {
            'user_id': user_id,
            'timestamp': time.time()
        }
```

### 用户任务列表缓存

```python
class UserTaskListCache:
    def __init__(self, ttl: int = 60):  # 1 分钟
        self.cache = {}
        self.ttl = ttl
    
    async def get(self, user_id: int) -> Optional[List[Task]]:
        """获取缓存的任务列表"""
        if user_id in self.cache:
            entry = self.cache[user_id]
            if time.time() - entry['timestamp'] < self.ttl:
                return entry['tasks']
            else:
                del self.cache[user_id]
        return None
    
    def set(self, user_id: int, tasks: List[Task]):
        """设置缓存"""
        self.cache[user_id] = {
            'tasks': tasks,
            'timestamp': time.time()
        }
```

## 监控和日志

### 关键指标

1. **消息处理成功率**: 成功处理的消息数 / 总消息数
2. **LLM 解析准确率**: 正确解析的消息数 / 总消息数
3. **任务匹配成功率**: 找到匹配任务的消息数 / 总消息数
4. **平均响应时间**: 所有请求的平均响应时间
5. **降级使用率**: 使用规则引擎的消息数 / 总消息数

### 日志记录

```python
# 回调接收日志
logger.info(f"Received dingtalk callback from {dingtalk_user_id}")

# 签名验证日志
logger.warning(f"Signature verification failed for {dingtalk_user_id}")

# LLM 调用日志
logger.info(f"LLM parsing took {elapsed_time}ms")

# 任务更新日志
logger.info(f"Task {task_id} updated from dingtalk feedback")

# 错误日志
logger.error(f"Error processing dingtalk callback: {error}")
```

## 部署检查清单

- [ ] 创建 DingtalkUserMapping 表
- [ ] 创建 ProgressFeedback 表
- [ ] 扩展 UserNotificationSettings 表
- [ ] 实现 DingtalkCallbackAPI
- [ ] 实现 ProgressParserService
- [ ] 实现 TaskMatcherService
- [ ] 实现 TaskUpdaterService
- [ ] 实现 MessageParserService
- [ ] 实现 MessagePrinterService
- [ ] 配置钉钉机器人 Webhook
- [ ] 配置 LLM 服务
- [ ] 设置异步任务队列
- [ ] 配置缓存系统
- [ ] 设置监控和告警
- [ ] 编写集成测试
- [ ] 编写属性测试
- [ ] 性能测试和优化
- [ ] 安全审计
- [ ] 文档编写
- [ ] 用户培训

