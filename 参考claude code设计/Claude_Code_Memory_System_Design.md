# Claude Code 记忆系统设计文档

> 基于 claude-source-leaked-main 源码分析

## 一、系统架构概览

Claude Code 的记忆系统是一个**三层架构**的持久化、以文件为基础的记忆系统：

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Memory System Architecture                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌───────────────────┐   ┌───────────────────┐  ┌───────────────┐  │
│  │   Auto Memory    │   │ Session Memory  │  │ Team Memory  │  │
│  │  (跨会话持久记忆)  │   │  (会话内摘要)   │  │  (团队共享)  │  │
│  └────────┬──────────┘   └───────┬────────┘   └──────┬──────┘  │
│           │                    │                 │               │
│           ▼                    ▼                 ▼               │
│  ┌──────────────────────────────────────────────────────┐    │
│  │              memdir/ (持久化存储)                      │    │
│  │   ~/.claude/projects/<slug>/memory/                   │    │
│  └──────────────────────────────────────────────────────┘    │
│                            │                                  │
│                            ▼                                  │
│              ┌─────────────────────────┐                   │
│              │ Extract Memories        │                   │
│              │ (自动持久化提取)        │                   │
│              └─────────────────────────┘                   │
│                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 核心存储路径

```typescript
// paths.ts - 记忆存储路径解析
getAutoMemPath() = {
  // 优先级：
  // 1. CLAUDE_COWORK_MEMORY_PATH_OVERRIDE (环境变量)
  // 2. autoMemoryDirectory (settings.json)
  // 3. ~/.claude/projects/<sanitized-cwd>/memory/
}

// 示例: ~/.claude/projects/C--Users-username/project-name/memory/
```

---

## 二、Auto Memory（自动记忆）- 跨会话持久化

### 2.1 记忆类型系统 (memoryTypes.ts)

Claude Code 定义了**四种严格的记忆类型**，强制分类防止记忆变成垃圾堆：

| 类型 | 英文名 | 作用域 | 描述 | 何时保存 |
|------|-------|--------|------|----------|
| **用户** | user | 私有 | 用户角色、目标、职责、知识背景 | 当了解用户的角色、偏好、职责时 |
| **反馈** | feedback | 私有/团队 | 用户给出的指导（偏好/避免的行动） | 当用户纠正你或确认某做法时 |
| **项目** | project | 私有/团队 | 项目背景（deadlines、incidents、决策） | 当了解项目目标、截止日期、谁做什么时 |
| **引用** | reference | 通常团队 | 外部系统指针（Linear、Slack） | 当了解外部系统位置时 |

**关键设计理念**：区分**可派生信息** vs **不可派生信息**

- 应该记住：用户偏好、项目背景、外部引用（不可从代码/git 推导）
- 不应记住：代码模式、git 历史、文件结构（可以从代码推导）

### 2.2 文件存储格式 (memoryTypes.ts)

每个记忆文件使用 **YAML frontmatter** 格式：

```markdown
---
name: user_role
description: 用户是数据科学家，专注于可观测性/日志
type: user
---

用户是一名资深数据科学家，目前专注于构建可观测性系统...
```

**入口文件 MEMORY.md**（不是存储文件，是索引）：

```markdown
# Auto Memory

You have a persistent, file-based memory system at `~/.claude/projects/.../memory/`.

## Types of memory

...

## MEMORY.md

- [user_role](user_role.md) — 用户角色和专业知识背景
- [feedback_testing](feedback_testing.md) — 测试偏好
```

**限制规则**：

- `MEMORY.md`：最多 200 行
- `MEMORY.md`：最多 25KB
- 每行一个链接：`- [Title](file.md) — one-line hook`

### 2.3 相关记忆发现 (findRelevantMemories.ts)

**问题**：面对大量记忆文件，如何选择最相关的？

**解决方案**：`findRelevantMemories()` 函数

```typescript
// 核心流程
async function findRelevantMemories(
  query: string,           // 用户当前 Query
  memoryDir: string,       // 记忆目录
  signal: AbortSignal,
  recentTools: string[],   // 最近使用的工具
  alreadySurfaced: Set    // 已加载的记忆
): Promise<RelevantMemory[]>
```

流程：

```
用户 Query
    │
    ▼
1. scanMemoryFiles(memoryDir)
   - 扫描目录中所有 .md 文件
   - 读取 frontmatter (filename, description, type, mtime)
   - 最多返回 200 个，按时间排序
    │
    ▼
2. formatMemoryManifest(memories)
   - 构建清单：[type] filename (timestamp): description
    │
    ▼
3. sideQuery() 调用 Sonnet 选择
   - System: "选择最相关的记忆（最多5个）"
   - Input: "Query: {用户问题}\n\nAvailable memories:\n{manifest}"
   - Output: JSON { selected_memories: [filename, ...] }
    │
    ▼
4. 返回 RelevantMemory[]
   [{ path: filePath, mtimeMs: timestamp }, ...]
```

**实现代码要点**：

```typescript
// findRelevantMemories.ts:39-75
const SELECT_MEMORIES_SYSTEM_PROMPT = `You are selecting memories that will be useful to Claude Code as it processes a user's query.

Return a list of filenames for the memories that will clearly be useful (up to 5).
- If you are unsure if a memory will be useful, do not include it.
- If there are no useful memories, return an empty list.
- If recently-used tools are provided, do NOT select their documentation (noise).
`

const selectedFilenames = await sideQuery({
  model: getDefaultSonnetModel(),
  system: SELECT_MEMORIES_SYSTEM_PROMPT,
  messages: [{ role: 'user', content: `Query: ${query}\n\nAvailable memories:\n${manifest}` }],
  max_tokens: 256,
  output_format: { type: 'json_schema', schema: {...} }
})
```

### 2.4 System Prompt 构建 (memdir.ts)

**核心函数**：`loadMemoryPrompt()`

```typescript
// memdir.ts:419-507
async function loadMemoryPrompt(): Promise<string | null> {
  // 1. 检查 auto memory 是否启用
  const autoEnabled = isAutoMemoryEnabled()

  // 2. 检查 team memory 是否启用
  if (feature('TEAMMEM') && teamMemPaths.isTeamMemoryEnabled()) {
    // 组合模式：个人 + 团队
    return teamMemPrompts.buildCombinedMemoryPrompt(...)
  }

  // 3. 单个人模式
  if (autoEnabled) {
    return buildMemoryLines('auto memory', autoDir, ...).join('\n')
  }

  return null
}
```

**构建内容**：

```typescript
// memdir.ts:199-266
function buildMemoryLines(displayName, memoryDir, extraGuidelines?, skipIndex?): string[] {
  return [
    `# ${displayName}`,
    `You have a persistent, file-based memory system at \`${memoryDir}\`.`,
    '',
    // 1. 记忆类型定义 (TYPES_SECTION_INDIVIDUAL)
    ...TYPES_SECTION_INDIVIDUAL,
    '',
    // 2. 什么不应保存 (WHAT_NOT_TO_SAVE_SECTION)
    ...WHAT_NOT_TO_SAVE_SECTION,
    '',
    // 3. 如何保存
    '## How to save memories',
    ...['两步流程：1. 写文件 2. 更新索引'],
    '',
    // 4. 何时访问 (WHEN_TO_ACCESS_SECTION)
    ...WHEN_TO_ACCESS_SECTION,
    '',
    // 5. 信任回忆的警告 (TRUSTING_RECALL_SECTION)
    ...TRUSTING_RECALL_SECTION,
    '',
    // 6. Memory vs Plan vs Task 区别
    '## Memory and other forms of persistence',
    ...
  ]
}
```

**关键设计**：

- 目录已存在 → 直接写入（不需要 mkdir 检查）
- 相对日期 → 转换为绝对日期（"Thursday" → "2026-03-05"）
- 过时记忆 → 验证后更新或删除

---

## 三、Session Memory（会话记忆）- 会话内摘要

### 3.1 设计问题

- Auto Memory 太慢，不适合频繁更新
- 上下文窗口有上限 (~200K tokens)
- 需要在长会话中保持关键信息

### 3.2 解决方案：Forked Subagent 提取

**核心思路**：使用 `runForkedAgent()` 在后台 fork 子代理，异步提取会话摘要

```typescript
// sessionMemory.ts:272-350
const extractSessionMemory = sequential(async function (context: REPLHookContext) {
  // 1. 检查是否在主线程
  if (context.querySource !== 'repl_main_thread') return

  // 2. 检查门控
  if (!isSessionMemoryGateEnabled()) return

  // 3. 检查阈值
  if (!shouldExtractMemory(messages)) return

  // 4. 创建隔离的上下文
  const setupContext = createSubagentContext(toolUseContext)

  // 5. 设置文件
  const { memoryPath, currentMemory } = await setupSessionMemoryFile(setupContext)

  // 6. 构建提取提示
  const userPrompt = await buildSessionMemoryUpdatePrompt(currentMemory, memoryPath)

  // 7. Fork 执行
  await runForkedAgent({
    promptMessages: [createUserMessage({ content: userPrompt })],
    cacheSafeParams: createCacheSafeParams(context),
    canUseTool: createMemoryFileCanUseTool(memoryPath),
    querySource: 'session_memory',
    forkLabel: 'session_memory',
  })
})
```

### 3.3 触发阈值 (sessionMemoryUtils.ts)

```typescript
// 默认配置
DEFAULT_SESSION_MEMORY_CONFIG = {
  minimumMessageTokensToInit: 8000,      // 首次摘要 token 数
  minimumTokensBetweenUpdate: 10000,      // 两次摘要最小间隔
  toolCallsBetweenUpdates: 20,           // 最小 tool 调用数
}

// 触发条件
function shouldExtractMemory(messages): boolean {
  const currentTokenCount = tokenCountWithEstimation(messages)

  // 1. 未初始化？检查首次阈值
  if (!isSessionMemoryInitialized()) {
    return hasMetInitializationThreshold(currentTokenCount)
  }

  // 2. 检查阈值组合
  const hasMetTokenThreshold = hasMetUpdateThreshold(currentTokenCount)
  const hasMetToolCallThreshold = toolCallsSinceLastUpdate >= 20
  const hasToolCallsInLastTurn = hasToolCallsInLastAssistantTurn(messages)

  // 触发：token 阈值 AND (tool 调用阈值 OR 无 tool 调用)
  return (hasMetTokenThreshold && hasMetToolCallThreshold) ||
         (hasMetTokenThreshold && !hasToolCallsInLastTurn)
}
```

**关键设计**：

- token 阈值：始终必须（防止过度提取）
- tool 调用阈值：在自然对话停顿点提取
- "无 tool 调用"检查：在对话的自然停顿点提取

### 3.4 隔离执行环境

```typescript
// sessionMemory.ts:460-482
function createMemoryFileCanUseTool(memoryPath: string): CanUseToolFn {
  return async (tool: Tool, input: unknown) => {
    // 仅允许 Edit 特定 memory 文件
    if (tool.name === FILE_EDIT_TOOL_NAME &&
        typeof input === 'object' &&
        'file_path' in input &&
        input.file_path === memoryPath) {
      return { behavior: 'allow', updatedInput: input }
    }
    return { behavior: 'deny', message: `only Edit on ${memoryPath} allowed` }
  }
}
```

---

## 四、Extract Memories（持久记忆提取）

### 4.1 工作时机

- 在每个完整查询循环结束时运行（模型产生最终响应，无 tool 调用）
- 使用 forked agent 不阻塞主对话

### 4.2 Mutual Exclusion 设计

```typescript
// extractMemories.ts:348-360
// 主 Agent 已写入记忆？跳过提取
if (hasMemoryWritesSince(messages, lastMemoryMessageUuid)) {
  // 跳过 + 更新 cursor
  lastMemoryMessageUuid = lastMessage.uuid
  return
}
```

**关键**：防止重复提取。

### 4.3 频率控制

```typescript
// 每 N 个 eligible turn 运行一次
getFeatureValue('tengu_bramble_lintel', 1)  // 默认每个 turn
```

### 4.4 权限控制 (extractMemories.ts:171-222)

```typescript
// 允许的工具：Read/Grep/Glob (无限制)
// 允许的 Bash：仅 read-only 命令
// ���允许的 Write/Edit：memory 目录内
function createAutoMemCanUseTool(memoryDir: string): CanUseToolFn {
  return async (tool, input) => {
    // Read/Grep/Glob: 允许
    if ([FILE_READ_TOOL_NAME, GREP_TOOL_NAME, GLOB_TOOL_NAME].includes(tool.name)) {
      return { behavior: 'allow' }
    }
    // Bash: 必须是 read-only
    if (tool.name === BASH_TOOL_NAME && tool.isReadOnly(input)) {
      return { behavior: 'allow' }
    }
    // Edit/Write: 必须在 memory 目录
    if ([FILE_EDIT_TOOL_NAME, FILE_WRITE_TOOL_NAME].includes(tool.name)) {
      if (isAutoMemPath(input.file_path)) {
        return { behavior: 'allow' }
      }
    }
    return { behavior: 'deny' }
  }
}
```

---

## 五、Team Memory（团队记忆）

### 5.1 目录结构

```
~/.claude/projects/<slug>/memory/
├── MEMORY.md              # 个人索引
├── team/
│   ├── MEMORY.md        # 团队索引
│   ├── *.md             # 团队记忆文件
└── *.md                 # 个人记忆文件
```

### 5.2 Scope 指导

| 类型 | Scope |
|------|-------|
| user | 始终私有 |
| feedback | 默认私有，除非是项目级 convention |
| project | 默认团队 |
| reference | 通常团队 |

---

## 六、Forked Agent 模式

### 6.1 核心问题

如何在不阻塞主对话的情况下执行后台任务？

### 6.2 解决方案：runForkedAgent()

```typescript
// forkedAgent.ts:83-113
await runForkedAgent({
  promptMessages: [createUserMessage({ content: userPrompt })],
  cacheSafeParams: createCacheSafeParams(context),  // 共享父 prompt cache
  canUseTool: createMemoryFileCanUseTool(memoryPath),  // 隔离权限
  querySource: 'session_memory',
  forkLabel: 'session_memory',
  // 关键：隔离的文件状态
  overrides: { readFileState: setupContext.readFileState }
})
```

### 6.3 设计要点

1. **Prompt Cache 共享**：复制父会话的 system prompt cache，实现零成本启动
2. **隔离的文件系统**：使用独立的 readFileState，防止污染父状态
3. **受限的工具权限**：仅允许操作特定文件
4. **并行执行**：不阻塞主流程

---

## 七、关键文件索引

| 文件 | 职责 |
|------|------|
| `src/memdir/memdir.ts` | 记忆系统入口、System Prompt 构建 |
| `src/memdir/memoryTypes.ts` | 记忆类型定义、行为指导文本 |
| `src/memdir/findRelevantMemories.ts` | 相关记忆发现问题 |
| `src/memdir/memoryScan.ts` | 记忆文件扫描、frontmatter 解析 |
| `src/memdir/paths.ts` | 记忆路径解析、启用控制 |
| `src/services/SessionMemory/sessionMemory.ts` | 会话内摘要提取 |
| `src/services/SessionMemory/sessionMemoryUtils.ts` | 阈值配置、状态管理 |
| `src/services/SessionMemory/prompts.ts` | 提取提示构建 |
| `src/services/extractMemories/extractMemories.ts` | 持久记忆自动提取 |
| `src/services/extractMemories/prompts.ts` | 提取提示词 |
| `src/utils/forkedAgent.ts` | Forked Agent 工具 |
| `src/utils/frontmatterParser.ts` | Frontmatter 解析 |

---

## 八、数据流总结

```
用户输入
    │
    ▼
processUserInput()              ← 输入预处理、斜杠命令解析
    │
    ▼
QueryEngine.submitMessage()     ← 会话管理
    │
    ├─ fetchSystemPromptParts()
    │   ├─ getSystemPrompt()        ← 静态部分
    │   ├─ getUserContext()          ← CLAUDE.md
    │   ├─ loadMemoryPrompt()         ← 加载 Memory
    │   └─ getSystemContext()       ← Git 状态
    │
    ▼
API 调用 (流式)
    │
    ├─ 工具调用循环
    │   └─ toolOrchestration.ts
    │
    └─ 后处理 (Post-processing)
        ├─ 成本追踪
        ├─ 上下文压缩
        ├─ extractMemories()         ← 自动持久化记忆
        ├─ sessionMemory.extract() ← 会话摘要
        └─ 标题建议
```

---

## 九、设计决策总结

### 9.1 记忆类型数量

- **固定 3-4 种类型**：防止无结构增长
- **推荐**：用户、反馈、项目、引用

### 9.2 存储格式

- **YAML frontmatter + Markdown 内容**
- **原因**：可读、可解析、易版本控制

### 9.3 提取时机

- **方案 A**：每 N 个 turn 提取（简单）
- **方案 B**：阈值触发（token + tool 调用）更精细
- **推荐**：两者结合

### 9.4 隔离 vs 共享

- **短期会话**：共享状态
- **长期持久化**：隔离的子 agent 提取

### 9.5 记忆检索

- **方案 A**：向量化相似度（重）
- **方案 B**：BM25 关键词（轻）
- **方案 C**：LLM 摘要选择（Claude Code 采用）
- **推荐**：对于简单场景用方案 C，对于大量记忆用 A+B 混合

---

*文档生成时间：2026-04-29*
*基于 claude-source-leaked-main 项目源码分析*