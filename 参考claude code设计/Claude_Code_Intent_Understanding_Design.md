# Claude Code 意图理解与执行系统设计文档

> 基于 claude-source-leaked-main 源码分析

## 一、核心问题与解决思路

**你的痛点**：AI 很难理解用户意图 → 回答不精准

**Claude Code 的解决思路**：分层处理 + 结构化输入 + System Prompt 引导 + 工具编排

```
┌─────────────────────────────────────────────────────────────────────┐
│                  Intent Understanding Pipeline                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  User Input                                                         │
│      │                                                              │
│      ▼                                                              │
│  ┌─────────────────┐                                                │
│  │ 1. 输入预处理   │  ← processUserInput.ts                        │
│  │ - 斜杠命令解析  │   - 模式识别                                   │
│  │ - 附件提取     │   - 意图分类                                   │
│  │ - 图片处理     │   - 参数提取                                   │
│  └────────┬────────┘                                                │
│           │                                                        │
│           ▼                                                        │
│  ┌─────────────────┐                                                │
│  │ 2. 查询引擎     │  ← QueryEngine.ts                            │
│  │ - System Prompt │   - 构建上下文                                │
│  │ - 消息历史     │   - 意图理解准备                              │
│  │ - 权限检查     │   - 决策规则                                  │
│  └────────┬────────┘                                                │
│           │                                                        │
│           ▼                                                        │
│  ┌─────────────────┐                                                │
│  │ 3. API 调用     │  ← Claude API                               │
│  │ - 意图理解     │   - 解析用户意图                             │
│  │ - 响应生成     │   - 生成回答                                 │
│  │ - 工具调用决策│   - 决定使用工具                              │
│  └────────┬────────┘                                                │
│           │                                                        │
│           ▼                                                        │
│  ┌─────────────────┐                                                │
│  │ 4. 工具执行循环│  ← toolOrchestration.ts                     │
│  │ - 权限检查     │   - 依赖分析                                 │
│  │ - 并行/串行执行│   - 结果处理                                 │
│  │ - 结果注入     │   - 上下文更新                               │
│  └────────┬────────┘                                                │
│           │                                                        │
│           ▼                                                        │
│  Response                                                         │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 二、第一层：输入预处理 (processUserInput.ts)

### 2.1 核心职责

将用户输入转换为结构化的消息序列，为后续处理做准备。

### 2.2 输入模式

```typescript
// types/textInputTypes.ts
type PromptInputMode =
  | 'prompt'   // 正常对话 - "帮我看看这个函数"
  | 'bash'      // Bash 命令模式 - "cat file.txt"
  | 'print'     // 打印模式 - 输出到 stdout
  | 'auto'      // 自动模式 - 系统决定
```

### 2.3 斜杠命令解析 (processSlashCommand.tsx)

```typescript
// 核心流程
parseSlashCommand(input: string) → {
  commandName: string,  // e.g., "git", "commit", "branch"
  args: string,         // 命令参数
  attachments: [],     // 附件
}

// 示例输入：
// "/git commit -m 'fix bug' file.ts"
// → { commandName: 'git', args: 'commit -m "fix bug" file.ts' }
```

### 2.4 Why 斜杠命令重要

斜杠命令是**明确的意图信号**：

| 输入 | 含义 | 处理方式 |
|------|------|----------|
| `/git commit` | "我要提交代码" | 直接执行 git 命令 |
| "帮我看看git" | 模糊 | 需理解后执行 |
| `/plan` | "我要规划" | 进入计划模式 |
| "怎么做" | 需解释 | 分析后回答 |

---

## 三、第二层：查询引擎 (QueryEngine.ts)

### 3.1 System Prompt 构建 (queryContext.ts)

这是**意图理解的核心**，给 AI 上下文让它"能理解"：

```typescript
// 核心流程
fetchSystemPromptParts({ tools, mainLoopModel, mcpClients })
  → {
      defaultSystemPrompt:  // 静态部分
      userContext: {       // CLAUDE.md 内容
        project: string,
        global: string
      },
      systemContext: {     // 动态部分
        cwd: string,
        gitStatus: string,
        branch: string
      }
    }
```

### 3.2 System Prompt 组成部分

```typescript
// prompts.ts - 实际示例结构
const SYSTEM_PROMPT = [
  // 1. 身份定义
  `You are Claude Code, Anthropic's official CLI...`,
  
  // 2. 工具说明 (带有选择规则)
  `## Tools
  
  **Read**: Use when you need to see contents before making changes.
  - Always use Read before Edit/Write to a file you haven't read.
  - Use Read to understand code structure, not to search.
  
  **Edit**: Use when you need targeted changes.
  - Use when you know exactly what to change.
  - Do NOT use for large refactoring; Use Write instead.
  
  **Write**: Use when you need new files or large changes.
  - Use for new files, or when change is too large for Edit.`,

  // 3. 行为规则
  `## How to work
  
  - When the user asks a question, answer it directly.
  - When you need to make changes, explain first.
  - When uncertain, ask for clarification.`,

  // 4. Memory (用户背景)
  loadMemoryPrompt(),
  
  // 5. 环境信息
  getSystemContext()
]
```

### 3.3 关键设计：工具选择规则

**不是列出工具，而是给出选择规则**：

```typescript
// 来自 tool-system.md 的架构文档
const TOOL_SELECTION_GUIDANCE = `
// 决策树示例

Q: 用户要求做什么？
├─ "找出"/"搜索"/"找找" → 需要搜索
│   ├─ 知道具体文件名？→ Glob
│   └─ 不知道文件名？→ Grep/Embedded Search
│
├─ "修改"/"改"/"更新" → 需要修改
│   ├─ 精确位置？→ Edit
│   └─ 大范围？→ Write
│
├─ "创建"/"新建设" → 需要创建
│   └─ Write
│
├─ "怎么做"/"如何实现" → 需要规划
│   └─ 建议 /plan
│
└─ "运行"/"执行" → 需要执行
    ├─ Shell 命令？→ Bash
    └─ 特殊？→ MCP Tool
`
```

---

## 四、第三层：API 调用 (query.ts)

### 4.1 核心查询循环

```typescript
// query.ts - 简化流程
async function* query(config: QueryConfig): AsyncGenerator<SDKMessage> {
  // 1. 构建消息
  const messages = buildMessages(config.input)

  // 2. 循环直到无 tool 调用
  while (true) {
    // 3. 调用 API
    const response = await callClaudeAPI(messages)

    // 4. 处理响应
    if (response.type === 'text') {
      yield response
      break  // 完成
    }

    if (response.type === 'tool_use') {
      // 5. 执行工具
      const toolResult = await executeTool(response.tool)

      // 6. 注入结果
      messages.push(toolResult)

      // 7. 继续循环
      continue
    }
  }
}
```

### 4.2 意图理解在 API 层面

Claude API 接收：
- systemPrompt（含工具规则）
- messages（含当前对话历史）
- tools（含工具定义）

**输出**：
- 文本响应
- tool_use 请求

**关键**：意图理解发生在 API 内部，systemPrompt 提供了决策框架。

---

## 五、第四层：工具编排 (toolOrchestration.ts)

### 5.1 核心职责

管理多个工具的执行，处理依赖关系和并行化。

### 5.2 并行/串行分析

```typescript
// toolOrchestration.ts - 核心逻辑
async function orchestrateTools(toolCalls: ToolUse[]) {
  // 1. 依赖分析
  const dependencyGraph = analyzeDependencies(toolCalls)

  // 2. 分组
  const { parallel, sequential } = dependencyGraph

  // 3. 并行执行无依赖
  if (parallel.length > 0) {
    const results = await Promise.all(
      parallel.map(tool => executeTool(tool))
    )
  }

  // 4. 串行执行有依赖
  for (const tool of sequential) {
    const result = await executeTool(tool)
  }
}
```

### 5.3 权限检查

```typescript
// toolExecution.ts
async function executeToolWithPermission(toolUse: ToolUse) {
  // 1. 权限检查
  const decision = await canUseTool(toolUse.tool, toolUse.input)

  if (decision.behavior === 'deny') {
    // 拒绝，返回错误
    return createToolResult(toolUse.id, {
      type: 'error',
      error: decision.message
    })
  }

  // 2. 执行
  const result = await toolUse.tool.execute(decision.updatedInput)

  // 3. 返回结果
  return createToolResult(toolUse.id, result)
}
```

---

## 六、意图分类与处理策略

### 6.1 意图类型

Claude Code 把用户意图分为几类：

| 意图类型 | 特征词 | 处理策略 |
|---------|--------|----------|
| **简单查询** | "是什么" / "怎么" | 直接回答 |
| **执行任务** | "做" / "帮我" | 工具调用循环 |
| **规划需求** | "如何实现" / "方案" | 进入计划模式 |
| **信息收集** | "找出所有" | 搜索聚合 |
| **复杂任务** | 多步骤 | Agent 子代理 |

### 6.2 规划模式 (EnterPlanModeTool)

```
用户: "添加用户认证"
    │
    ▼
检测到复杂任务或用户输入 /plan
    │
    ▼
┌──────────────────────────┐
│ Plan Agent (只读模式)     │
│ - 分析代码结构           │
│ - 设计实现方案           │
│ - 不修改文件             │
└────────────┬─────────────┘
             │
             ▼
返回实现计划供���户���批
```

---

## 七、System Prompt 中的关键设计模式

### 7.1 决策规则模式

```typescript
// 核心：给出决策树，不是工具列表
const DECISION_RULES = `
When you need to work with files:

1. **Reading first**
   - If you need to see what's in a file → Read
   - If you need to understand structure → Read
   - If you need to find specific text → Grep

2. **Making changes**
   - If you know EXACTLY what to change → Edit
   - If you're unsure of the location → Read first, then Edit
   - If it's a new file or big change → Write

3. **Running commands**
   - If you need to run a command → Bash
   - If the command is read-only (ls, grep) → allowed
   - If the command modifies state → requires permission

4. **When unsure**
   - Ask the user clarifying questions
   - Don't assume
   - Verify before acting
`
```

### 7.2 置信度引导

```typescript
const CONFIDENCE_GUIDANCE = `
- If you're confident in your answer: answer directly
- If you're uncertain: show your reasoning, then answer
- If you need more info: ask the user
- If you'd modify files: confirm first
- If you're not sure something exists: verify first
`
```

### 7.3 验证模式

```typescript
const VERIFICATION_RULES = `
Before recommending from memory:
- "The memory says X exists" ≠ "X exists now"
- If recommending a file: verify it exists
- If recommending code: verify it compiles
- If you're not sure: check first, then recommend
`
```

---

## 八、后处理机制

### 8.1 意图纠正反馈

```typescript
// 当 AI 理解错误时，用户可以纠正
// → 保存为 feedback 类型记忆
// 示例：
// user: "我不是说这个，是那个"
// → saveMemory('feedback', '当用户说 X 时，实际意思是 Y')
```

### 8.2 从反馈学习

```typescript
// memoryTypes.ts - feedback 类型定义
const FEEDBACK_EXAMPLE = `
user: stop summarizing what you just did at the end of every response
assistant: [saves feedback: this user wants terse responses, no trailing summaries]

user: yeah the single bundled PR was the right call
assistant: [saves feedback: for refactors, user prefers one bundled PR over many small ones]
`
```

---

## 九、关键源码文件

| 文件 | 职责 |
|------|------|
| `src/utils/processUserInput/processUserInput.ts` | 输入预处理 |
| `src/utils/processUserInput/processSlashCommand.tsx` | 斜杠命令解析 |
| `src/QueryEngine.ts` | 核心查询引擎 (~1300行) |
| `src/query.ts` | 查询循环 (~1700行) |
| `src/utils/queryContext.ts` | System Prompt 构建 |
| `src/constants/prompts.ts` | System Prompt 规则定义 |
| `src/services/tools/toolOrchestration.ts` | 工具编排 (~600行) |
| `src/services/tools/toolExecution.ts` | 工具执行 |
| `src/architecture/query-lifecycle.md` | 生命周期文档 |
| `src/architecture/tool-system.md` | 工具系统文档 |
| `src/commands/` | 斜杠命令实现 |

---

## 十、给你的设计建议

### 10.1 输入层：强化意图信号

```typescript
// 方法1：结构化输入格式
Intent = {
  action: "read" | "search" | "edit" | "create",
  target: string,
  constraint: string
}

// 方法2：意图前缀
// [READ] src/index.ts
// [SEARCH] "function" src/**/*.ts
```

### 10.2 上下文层：决策规则

```typescript
const INTENT_HANDLING = `
When user input contains:
1. "找出"/"找到"/"搜索" → Search tool
2. "修改"/"改" → Read then Edit
3. "创建"/"新建" → Write
4. "怎么做"/"如何实现" → Suggest /plan
5. "列出"/"列表" → Aggregate results
`
```

### 10.3 输出层：验证理解

```typescript
const CONFIRMATION = `
Before executing:
1. 你要做什么：
2. 你会用哪些工具：
3. 期望结果：
确认请回复 "我将..."
`
```

### 10.4 反馈循环

```typescript
// 当理解错误时
feedback("你的理解有偏差，实际需求是...")
// 记录
saveMemory('feedback', '当用户说 X 时，实际意思是 Y')
```

---

## 十一、简化的设计架构

如果要快速实现：

```
模块：
1. IntentParser    - 解析输入，提取意图
2. ContextBuilder - 构建上下文（Memory、CLAUDE.md）
3. PlanGenerator - 生成执行计划
4. Executor      - 执行并反馈
5. FeedbackLoop - 从纠正中学习
```

核心流程：

```
Input → IntentParser.parse() 
     → IntentClassifier.classify()
     → ContextBuilder.build()
     → PlanGenerator.generate()
     → Executor.execute()
     → FeedbackLoop.learn()
```

---

*文档生成时间：2026-04-29*
*基于 claude-source-leaked-main 项目源码分析*