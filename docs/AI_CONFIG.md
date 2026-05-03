---
source: 工作文档
author: HMF
created: 2026-04-10
description: "TaskTree AI功能配置指南，包含Minimax/OpenAI/Anthropic三大模型提供商配置"
tags:
  - Status/Done
  - Type/Work/SOP
  - Area/Lab
  - Tech/Python
  - Tech/Frontend
---

# AI 功能配置指南

## 问题说明

如果你在使用 AI 分析、AI 智能创建等功能时遇到"AI 对话失败"或"未配置大模型服务"的错误，说明需要配置 LLM API Key。

## 配置步骤

### 1. 选择 LLM 提供商

TaskTree 支持以下大模型提供商：

- **Minimax**（推荐，国内访问快）
  - 模型：MiniMax-M2.7, abab6.5s-chat, abab6.5g-chat
  - 官网：https://www.minimaxi.com/
  
- **OpenAI**
  - 模型：gpt-4o, gpt-4o-mini, gpt-4-turbo
  - 官网：https://platform.openai.com/
  
- **Anthropic**
  - 模型：claude-sonnet-4, claude-3-opus, claude-3-haiku
  - 官网：https://www.anthropic.com/

### 2. 获取 API Key

以 Minimax 为例：

1. 访问 https://www.minimaxi.com/
2. 注册并登录账号
3. 进入控制台，创建 API Key
4. 复制 API Key 和 Group ID（如果需要）

### 3. 配置环境变量

编辑项目根目录的 `.env` 文件，添加以下配置：

```bash
# LLM 大模型配置
LLM_PROVIDER=minimax          # 提供商: minimax, openai, anthropic
LLM_API_KEY=your-api-key-here # 替换为你的 API Key
LLM_MODEL=MiniMax-M2.7        # 模型名称
LLM_GROUP_ID=your-group-id    # Minimax 专用（可选）
```

**OpenAI 配置示例**：
```bash
LLM_PROVIDER=openai
LLM_API_KEY=sk-xxxxxxxxxxxxx
LLM_MODEL=gpt-4o-mini
```

**Anthropic 配置示例**：
```bash
LLM_PROVIDER=anthropic
LLM_API_KEY=sk-ant-xxxxxxxxxxxxx
LLM_MODEL=claude-sonnet-4-20250514
```

### 4. 重启后端服务

配置完成后，需要重启后端容器以加载新的环境变量：

```bash
# 重新构建并启动后端
docker-compose build backend
docker-compose up -d backend

# 或者重启所有服务
docker-compose restart
```

### 5. 测试 AI 功能

1. 打开项目详情页
2. 点击"AI 分析"按钮
3. 如果配置正确，应该能看到 AI 正在分析项目任务

## 常见问题

### Q: 提示"AI 响应超时"

**A**: 可能是网络问题或 API 服务繁忙，建议：
- 检查网络连接
- 稍后重试
- 如果使用 OpenAI，考虑切换到 Minimax（国内访问更快）

### Q: 提示"未配置大模型服务"

**A**: 说明 `.env` 文件中没有配置 `LLM_API_KEY`，请按照上述步骤配置。

### Q: 提示"API 调用频率超限"

**A**: API 调用次数超过限制，建议：
- 等待一段时间后重试
- 检查 API 账户的配额
- 升级 API 套餐

### Q: 如何验证配置是否正确？

**A**: 可以通过后端 API 测试连接：

```bash
# 进入后端容器
docker exec -it tasktree-backend bash

# 测试 LLM 连接（需要实现测试端点）
curl http://localhost:8000/api/v1/llm/test
```

## 支持的 AI 功能

配置完成后，以下功能将可用：

1. **AI 任务分析**：分析项目任务，识别风险和瓶颈
2. **AI 智能创建**：根据描述自动生成任务
3. **AI 任务修改**：智能修改任务属性
4. **AI 项目规划**：生成项目计划和时间表
5. **智能提醒**：基于任务状态的智能提醒

## 费用说明

- **Minimax**：新用户通常有免费额度，具体查看官网
- **OpenAI**：按 token 计费，gpt-4o-mini 较便宜
- **Anthropic**：按 token 计费，具体查看官网

建议先使用免费额度测试功能，确认满足需求后再考虑付费套餐。

## 安全建议

1. **不要将 API Key 提交到 Git**：`.env` 文件已在 `.gitignore` 中
2. **定期轮换 API Key**：建议每 3-6 个月更换一次
3. **限制 API Key 权限**：在提供商控制台设置最小权限
4. **监控 API 使用量**：定期检查 API 调用次数和费用

## 更多帮助

如果遇到其他问题，请查看：
- 项目文档：`docs/README.md`
- 技术方案：`docs/技术/技术方案.md`
- 开发记录：`docs/00-开发记录.md`
