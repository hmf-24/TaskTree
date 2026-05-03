---
source: 工作文档
author: HMF
created: 2026-04-10
description: "TaskTree 钉钉智能助手对接指南，包含Webhook和Stream模式配置"
tags:
  - Status/Done
  - Type/Work/SOP
  - Area/Lab
  - Tech/Python
---

# 钉钉智能助手对接指南

> [!info] 概述
> TaskTree 已集成钉钉智能助手功能，支持：
> - 钉钉消息回调接收
> - 用户身份绑定
> - AI 进度解析
> - 任务自动更新
> - 进度反馈记录

## 快速开始

### 1. 创建钉钉机器人

> [!tip] 快速开始
> 1. 登录钉钉开发者平台
> 2. 创建应用 → 选择"企业内部应用"
> 3. 获取应用凭证

#### 步骤 1: 登录钉钉开发者平台
访问 [钉钉开发者平台](https://open.dingtalk.com/)

#### 步骤 2: 创建应用
1. 点击"创建应用"
2. 选择"企业内部应用"
3. 填写应用信息：
   - 应用名称: TaskTree 智能助手
   - 应用描述: 任务进度智能管理
   - 应用类型: 机器人

> [!warning] 安全提醒
> 这些凭证是敏感信息，请通过环境变量配置，不要提交到代码仓库。

#### 步骤 3: 获取应用凭证
在应用详情页获取：
- `AppID`
- `AppSecret`
- `AgentID`

#### 步骤 4: 配置回调地址
1. 在应用设置中找到"消息接收"
2. 配置回调地址: `https://your-domain/api/v1/dingtalk/callback`
3. 配置签名密钥（自动生成）
4. 保存配置

### 2. 配置 TaskTree

#### 环境变量配置

在 `.env` 文件中添加：

```bash
# 钉钉配置
DINGTALK_APP_ID=your_app_id
DINGTALK_APP_SECRET=your_app_secret
DINGTALK_AGENT_ID=your_agent_id
DINGTALK_WEBHOOK_SECRET=your_webhook_secret
```

#### 数据库配置

系统会自动创建以下表：
- `dingtalk_user_mapping` - 用户身份映射
- `progress_feedback` - 进度反馈记录

### 3. 用户绑定

#### 前端绑定流程

1. 用户进入"设置" → "钉钉绑定"
2. 点击"绑定钉钉账号"
3. 扫描二维码或输入绑定码
4. 确认绑定

#### API 绑定

```bash
# 绑定钉钉账号
curl -X POST http://localhost:8000/api/v1/dingtalk/bind \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "dingtalk_user_id": "user123",
    "dingtalk_name": "张三"
  }'

# 查询绑定状态
curl -X GET http://localhost:8000/api/v1/dingtalk/binding \
  -H "Authorization: Bearer {token}"

# 解除绑定
curl -X DELETE http://localhost:8000/api/v1/dingtalk/unbind \
  -H "Authorization: Bearer {token}"
```

## 功能说明

### 消息回调处理

#### 支持的消息格式

用户可以通过钉钉发送以下格式的消息：

**1. 任务完成**
```
完成任务 A
已完成 任务 B
任务 C 完成了
```

**2. 任务进行中**
```
任务 A 进行中，进度 50%
任务 B 进度 75%
做到一半了
```

**3. 遇到问题**
```
任务 A 遇到问题：需要等待审批
任务 B 有问题：缺少资源
```

**4. 请求延期**
```
任务 A 需要延期 3 天
任务 B 延期一周
```

**5. 查询状态**
```
查询任务 A 的进度
任务 B 的状态是什么
```

#### 处理流程

```
钉钉消息
  ↓
签名验证 (HMAC-SHA256)
  ↓
时间戳验证 (5分钟窗口)
  ↓
用户身份查询
  ↓
AI 进度解析 (LLM)
  ↓
任务智能匹配
  ↓
任务自动更新
  ↓
钉钉回复确认
```

### AI 进度解析

系统使用 LLM 理解用户的自然语言消息，提取：
- **进度类型**: completed / in_progress / problem / extend / query
- **关键词**: 任务名称、描述片段
- **数值**: 进度百分比、延期天数
- **问题描述**: 用户报告的问题

### 任务匹配算法

系统使用多维度匹配算法：

| 匹配方式 | 权重 | 说明 |
|---------|------|------|
| 完全匹配任务名称 | 100 | 消息与任务名完全一致 |
| 任务名称包含关键词 | 80 | 任务名包含消息中的词 |
| 任务描述包含关键词 | 60 | 任务描述包含关键词 |
| 进行中/待处理状态 | +20 | 当前状态加权 |
| 最近更新的任务 | +10 | 时间加权 |

### 任务自动更新

根据解析结果自动更新：

| 进度类型 | 更新操作 | 说明 |
|---------|---------|------|
| completed | 状态 → 已完成, 进度 → 100% | 任务完成 |
| in_progress | 状态 → 进行中, 进度 → 用户指定值 | 更新进度 |
| problem | 在描述中追加问题记录 | 记录问题 |
| extend | 截止日期 → 延期 N 天 | 延期 |
| query | 返回任务当前状态 | 查询状态 |

## API 接口

### 1. 钉钉回调接口

> [!tip] 接口详情
> - 端点: `POST /api/v1/dingtalk/callback`
> - 认证: 钉钉签名 + 时间戳

```
POST /api/v1/dingtalk/callback

请求头:
  X-Dingtalk-Timestamp: 1234567890000
  X-Dingtalk-Sign: base64_encoded_signature

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

响应:
{
  "code": 0,
  "message": "success"
}
```

### 2. 用户绑定接口

```
POST /api/v1/dingtalk/bind

请求头:
  Authorization: Bearer {token}

请求体:
{
  "dingtalk_user_id": "dingtalk_user_123",
  "dingtalk_name": "张三"
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

### 3. 查询绑定状态

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

### 4. 解除绑定

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

### 5. 发送测试消息

```
POST /api/v1/dingtalk/test-message

请求头:
  Authorization: Bearer {token}

请求体:
{
  "message": "测试消息内容"
}

响应:
{
  "code": 0,
  "message": "消息发送成功"
}
```

### 6. 健康检查

```
GET /api/v1/dingtalk/health

响应:
{
  "code": 0,
  "data": {
    "status": "healthy",
    "dingtalk_service": "ok",
    "llm_service": "ok"
  }
}
```

## 安全性

> [!warning] 安全说明
> 所有回调请求都经过签名验证和时间戳检查，确保请求来自钉钉官方。

### 签名验证

所有回调请求都使用 HMAC-SHA256 签名验证：

```python
# 验证流程
timestamp = request.headers['X-Dingtalk-Timestamp']
sign = request.headers['X-Dingtalk-Sign']

# 构建签名字符串
string_to_sign = f"{timestamp}\n{secret}"

# 计算签名
hmac_obj = hmac.new(
    secret.encode('utf-8'),
    string_to_sign.encode('utf-8'),
    hashlib.sha256
)
computed_sign = base64.b64encode(hmac_obj.digest()).decode('utf-8')

# 验证
if computed_sign == sign:
    # 签名有效
    pass
```

### 时间戳验证

拒绝超过 5 分钟的请求，防止重放攻击：

```python
callback_time = int(timestamp) / 1000
current_time = time.time()
if abs(current_time - callback_time) > 300:
    # 请求已过期
    raise HTTPException(status_code=401, detail="请求已过期")
```

### 权限验证

- 用户只能更新自己负责的任务
- 项目成员可以查看项目任务
- 项目所有者可以管理项目成员

### 频率限制

- 每个用户每分钟最多 10 次请求
- 超过限制的请求会被拒绝

## 故障排查

> [!warning] 常见问题排查

### 问题 1: 回调请求无法接收

**症状**: 钉钉消息无响应

**解决方案**:
1. 检查回调地址是否正确配置
2. 确保服务器可以从互联网访问
3. 检查防火墙规则
4. 查看服务器日志

```bash
# 查看后端日志
docker-compose logs backend | grep dingtalk
```

### 问题 2: 签名验证失败

**症状**: 返回 401 错误

**解决方案**:
1. 确保 secret 配置正确
2. 检查时间戳是否在 5 分钟内
3. 验证签名算法是否正确

```bash
# 测试签名验证
curl -X POST http://localhost:8000/api/v1/dingtalk/callback \
  -H "X-Dingtalk-Timestamp: $(date +%s)000" \
  -H "X-Dingtalk-Sign: test_sign" \
  -H "Content-Type: application/json" \
  -d '{}'
```

### 问题 3: 用户未绑定

**症状**: 返回绑定引导消息

**解决方案**:
1. 用户需要先绑定钉钉账号
2. 访问系统设置进行绑定
3. 或使用 API 进行绑定

```bash
# 检查绑定状态
curl -X GET http://localhost:8000/api/v1/dingtalk/binding \
  -H "Authorization: Bearer {token}"
```

### 问题 4: 任务匹配失败

**症状**: 返回"未找到匹配的任务"

**解决方案**:
1. 检查任务名称是否正确
2. 确保任务属于当前用户
3. 尝试使用更具体的任务名称

```bash
# 测试消息处理
curl -X POST http://localhost:8000/api/v1/dingtalk/test-message \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"message": "测试消息"}'
```

## 性能指标

| 指标 | 目标 | 说明 |
|------|------|------|
| 回调响应时间 | < 200ms | API 响应时间 |
| LLM 解析时间 | < 3s | AI 处理时间 |
| 任务匹配时间 | < 500ms | 匹配算法耗时 |
| 并发处理能力 | 100 用户 | 支持的用户数 |

## 监控和日志

### 关键日志

```
# 回调接收
[INFO] Received dingtalk callback from {dingtalk_user_id}

# 签名验证
[WARNING] Signature verification failed for {dingtalk_user_id}

# LLM 调用
[INFO] LLM parsing took {elapsed_time}ms

# 任务更新
[INFO] Task {task_id} updated from dingtalk feedback

# 错误
[ERROR] Error processing dingtalk callback: {error}
```

### 监控指标

- 消息处理成功率
- LLM 解析准确率
- 任务匹配成功率
- 平均响应时间
- 降级使用率

## 最佳实践

### 1. 消息格式

使用清晰的消息格式以提高识别准确率：

```
✅ 好的格式:
- "完成任务 A"
- "任务 B 进度 50%"
- "任务 C 遇到问题：需要审批"

❌ 不好的格式:
- "a"
- "嗯"
- "搞定了"
```

### 2. 任务命名

使用清晰的任务名称以提高匹配准确率：

```
✅ 好的命名:
- "完成用户认证模块"
- "修复登录页面 Bug"
- "编写 API 文档"

❌ 不好的命名:
- "任务 1"
- "做一下"
- "xxx"
```

### 3. 错误处理

系统会自动处理错误并返回友好的提示：

```
- 用户未绑定 → 返回绑定引导
- 任务不存在 → 返回任务列表
- 消息格式错误 → 返回格式说明
- 系统错误 → 返回重试提示
```

## 常见问题

> [!question] Q: 如何修改已绑定的钉钉账号？

A: 先解除绑定，再重新绑定新账号：

```bash
# 解除绑定
curl -X DELETE http://localhost:8000/api/v1/dingtalk/unbind \
  -H "Authorization: Bearer {token}"

# 重新绑定
curl -X POST http://localhost:8000/api/v1/dingtalk/bind \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "dingtalk_user_id": "new_user_id",
    "dingtalk_name": "新昵称"
  }'
```

### Q: 如何禁用钉钉智能助手？

A: 在用户设置中禁用或删除 Webhook 配置

### Q: 支持哪些 LLM 提供商？

A: 支持 Minimax、OpenAI、Anthropic

### Q: 如何查看消息处理日志？

A: 查看后端日志：

```bash
docker-compose logs -f backend | grep dingtalk
```

## 相关文档

- [钉钉开发者文档](https://open.dingtalk.com/document)
- [[技术/API接口]] - TaskTree API 接口定义
- [[features/FEATURE_DINGTALK]] - 钉钉功能特性
- [[deployment/DEPLOYMENT]] - 部署指南

<!-- aliases: [钉钉集成] -->
