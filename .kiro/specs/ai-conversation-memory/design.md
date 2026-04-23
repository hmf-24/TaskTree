# AI 对话记忆功能 - 技术设计文档

## Overview

本文档定义了 TaskTree 项目「AI 对话记忆功能」的技术设计方案。该功能通过引入对话历史持久化和多场景 AI 助手,解决当前 AI 智能任务创建功能的核心痛点:每次对话都是全新开始,无法延续上下文,无法对现有任务进行分析和优化。

### 核心目标

1. **对话持久化**: 存储用户与 AI 的多轮对话历史,支持上下文延续
2. **多场景助手**: 提供任务创建、任务分析、任务修改、项目规划四种 AI 助手模式
3. **智能交互**: 基于对话历史理解用户意图,提供更精准的建议和操作
4. **无缝集成**: 与现有 LLM_Service 和任务管理功能深度集成

### 技术栈

- **后端**: FastAPI + SQLAlchemy + SQLite (异步)
- **前端**: React 18 + TypeScript + Ant Design + Zustand
- **LLM**: 复用现有 LLMService (支持 Minimax/OpenAI/Anthropic)
- **数据存储**: SQLite (新增 ai_conversations 表)


## Architecture

### 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend Layer                        │
├─────────────────────────────────────────────────────────────┤
│  AIAssistantPanel (统一 AI 助手面板)                         │
│  ├─ TaskCreatorMode (任务创建模式)                           │
│  ├─ TaskAnalyzerMode (任务分析模式)                          │
│  ├─ TaskModifierMode (任务修改模式)                          │
│  └─ ProjectPlannerMode (项目规划模式)                        │
│                                                               │
│  集成点:                                                      │
│  - ProjectDetail: "AI 分析" 按钮                             │
│  - TaskDetailDrawer: "AI 修改" 按钮                          │
│  - 扩展 AITaskCreatorModal: 对话历史支持                     │
└─────────────────────────────────────────────────────────────┘
                              ↓ HTTP/REST API
┌─────────────────────────────────────────────────────────────┐
│                        Backend Layer                         │
├─────────────────────────────────────────────────────────────┤
│  API Routes (conversations.py)                               │
│  ├─ POST   /conversations                                    │
│  ├─ POST   /conversations/{id}/messages                      │
│  ├─ GET    /conversations                                    │
│  ├─ GET    /conversations/{id}                               │
│  ├─ POST   /conversations/{id}/analyze                       │
│  ├─ POST   /conversations/{id}/modify                        │
│  ├─ POST   /conversations/{id}/plan                          │
│  └─ DELETE /conversations/{id}                               │
│                                                               │
│  Service Layer                                                │
│  ├─ AI_Conversation_Service (对话管理核心)                   │
│  │   ├─ 对话历史管理 (CRUD)                                  │
│  │   ├─ 上下文构建 (项目+任务数据)                           │
│  │   ├─ LLM 调用封装                                         │
│  │   └─ 消息压缩 (30条限制)                                  │
│  │                                                            │
│  ├─ Task_Analyzer (任务分析器)                               │
│  │   ├─ 获取项目任务数据                                     │
│  │   ├─ 调用 LLM 分析                                        │
│  │   └─ 返回结构化建议                                       │
│  │                                                            │
│  ├─ Task_Modifier (任务修改器)                               │
│  │   ├─ 解析自然语言意图                                     │
│  │   ├─ 生成修改操作                                         │
│  │   └─ 执行任务 API 调用                                    │
│  │                                                            │
│  └─ Project_Planner (项目规划器)                             │
│      ├─ 分析任务结构                                         │
│      ├─ 识别缺失环节                                         │
│      └─ 生成任务建议                                         │
│                                                               │
│  复用现有服务:                                                │
│  └─ LLM_Service (已有,支持 Minimax/OpenAI/Anthropic)        │
└─────────────────────────────────────────────────────────────┘
                              ↓ SQLAlchemy ORM
┌─────────────────────────────────────────────────────────────┐
│                        Data Layer                            │
├─────────────────────────────────────────────────────────────┤
│  SQLite Database                                              │
│  ├─ ai_conversations (新增)                                  │
│  ├─ tasks (已有)                                             │
│  ├─ projects (已有)                                          │
│  └─ users (已有)                                             │
└─────────────────────────────────────────────────────────────┘
```

### 数据流

#### 1. 任务分析流程

```
用户点击"AI 分析" 
  → Frontend 调用 POST /conversations (创建对话)
  → Frontend 调用 POST /conversations/{id}/analyze
  → AI_Conversation_Service 获取项目任务数据
  → Task_Analyzer 构建分析 prompt
  → LLM_Service 调用 LLM API
  → 解析 LLM 响应,提取分析结果
  → 保存对话历史
  → 返回结构化分析结果
  → Frontend 展示分析结果和建议
```

#### 2. 任务修改流程

```
用户输入修改指令 (如"把这个任务延后3天")
  → Frontend 调用 POST /conversations/{id}/messages
  → AI_Conversation_Service 加载对话历史
  → Task_Modifier 解析自然语言意图
  → LLM_Service 调用 LLM API 理解意图
  → Task_Modifier 生成修改操作 (如 {action: "update_due_date", task_id: 123, offset_days: 3})
  → 返回确认信息给用户
  → 用户确认后,Frontend 调用 POST /conversations/{id}/modify
  → Task_Modifier 执行 tasksAPI.update()
  → 保存对话历史
  → 返回执行结果
```

#### 3. 持续对话流程

```
用户发送消息
  → Frontend 调用 POST /conversations/{id}/messages
  → AI_Conversation_Service 加载对话历史 (最近30条)
  → 构建完整上下文 (system prompt + 对话历史 + 当前消息)
  → LLM_Service 调用 LLM API
  → 保存新消息到对话历史
  → 如果超过30条,自动移除最早的消息
  → 返回 AI 回复
  → Frontend 更新对话界面
```


## Components and Interfaces

### 后端组件

#### 1. AI_Conversation_Service

**职责**: 对话管理核心服务,负责对话历史的 CRUD、上下文构建、LLM 调用封装

**类定义**:

```python
# backend/app/services/ai_conversation_service.py

from typing import List, Dict, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from datetime import datetime, timezone
import json

from app.models import AIConversation, User, Project, Task
from app.services.llm_service import LLMService

class AIConversationService:
    """AI 对话服务"""
    
    MAX_MESSAGES = 30  # 最多保留30条消息 (15轮对话)
    MAX_CONTEXT_TOKENS = 4000  # 上下文 token 限制
    
    def __init__(self, db: AsyncSession, llm_service: LLMService):
        self.db = db
        self.llm_service = llm_service
    
    async def create_conversation(
        self,
        user_id: int,
        project_id: int,
        conversation_type: str,
        initial_message: Optional[str] = None
    ) -> AIConversation:
        """创建新对话"""
        pass
    
    async def get_conversation(
        self,
        conversation_id: int,
        user_id: int
    ) -> Optional[AIConversation]:
        """获取对话详情 (验证权限)"""
        pass
    
    async def list_conversations(
        self,
        user_id: int,
        project_id: Optional[int] = None,
        conversation_type: Optional[str] = None,
        limit: int = 20
    ) -> List[AIConversation]:
        """获取对话列表"""
        pass
    
    async def add_message(
        self,
        conversation_id: int,
        role: str,  # "user" | "assistant"
        content: str
    ) -> AIConversation:
        """添加消息到对话历史"""
        pass
    
    async def send_message(
        self,
        conversation_id: int,
        user_message: str,
        context_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """发送消息并获取 AI 回复"""
        pass
    
    async def build_context(
        self,
        conversation: AIConversation
    ) -> Dict[str, Any]:
        """构建对话上下文 (项目信息 + 任务数据)"""
        pass
    
    async def compress_messages(
        self,
        messages: List[Dict]
    ) -> List[Dict]:
        """压缩消息历史 (保留最近30条)"""
        pass
    
    async def delete_conversation(
        self,
        conversation_id: int,
        user_id: int
    ) -> bool:
        """删除对话"""
        pass
```

**关键方法实现**:

```python
async def send_message(
    self,
    conversation_id: int,
    user_message: str,
    context_data: Optional[Dict] = None
) -> Dict[str, Any]:
    """发送消息并获取 AI 回复"""
    
    # 1. 加载对话
    conversation = await self.get_conversation(conversation_id, user_id)
    if not conversation:
        raise ValueError("Conversation not found")
    
    # 2. 添加用户消息
    await self.add_message(conversation_id, "user", user_message)
    
    # 3. 构建上下文
    context = await self.build_context(conversation)
    
    # 4. 构建 LLM 消息
    messages = self._build_llm_messages(
        conversation.conversation_type,
        conversation.messages,
        context
    )
    
    # 5. 调用 LLM
    try:
        response = await self.llm_service.chat(
            messages=messages,
            temperature=0.7,
            max_tokens=2000
        )
    except Exception as e:
        # 错误处理
        raise
    
    # 6. 保存 AI 回复
    await self.add_message(conversation_id, "assistant", response)
    
    # 7. 压缩消息历史
    if len(conversation.messages) > self.MAX_MESSAGES:
        conversation.messages = conversation.messages[-self.MAX_MESSAGES:]
        await self.db.commit()
    
    return {
        "reply": response,
        "conversation_id": conversation_id,
        "message_count": len(conversation.messages)
    }
```

#### 2. Task_Analyzer

**职责**: 任务分析器,分析项目任务并生成优化建议

**类定义**:

```python
# backend/app/services/task_analyzer.py

from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from app.models import Project, Task
from app.services.llm_service import LLMService

class TaskAnalyzer:
    """任务分析器"""
    
    def __init__(self, db: AsyncSession, llm_service: LLMService):
        self.db = db
        self.llm_service = llm_service
    
    async def analyze_project_tasks(
        self,
        project_id: int,
        user_id: int,
        focus_areas: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """分析项目任务"""
        pass
    
    async def _get_project_tasks(
        self,
        project_id: int
    ) -> List[Task]:
        """获取项目所有任务"""
        pass
    
    async def _build_analysis_prompt(
        self,
        project: Project,
        tasks: List[Task],
        focus_areas: Optional[List[str]]
    ) -> str:
        """构建分析 prompt"""
        pass
    
    async def _parse_analysis_response(
        self,
        response: str
    ) -> Dict[str, Any]:
        """解析 LLM 分析响应"""
        pass
```

**分析 Prompt 模板**:

```python
ANALYSIS_PROMPT_TEMPLATE = """你是一个资深项目管理专家。请分析以下项目的任务情况:

项目名称: {project_name}
任务总数: {task_count}
已完成: {completed_count}
进行中: {in_progress_count}
待开始: {pending_count}

任务详情:
{task_details}

请从以下维度分析:
1. 任务瓶颈: 识别阻塞项目进度的关键任务
2. 时间冲突: 发现截止日期冲突或不合理的任务
3. 优先级问题: 指出优先级设置不合理的任务
4. 延期风险: 预测可能延期的任务
5. 资源分配: 分析任务负载是否均衡

返回 JSON 格式:
{{
  "summary": "整体评估摘要",
  "issues": [
    {{
      "type": "bottleneck|conflict|priority|risk|resource",
      "severity": "high|medium|low",
      "task_ids": [1, 2, 3],
      "description": "问题描述",
      "suggestion": "优化建议"
    }}
  ],
  "recommendations": [
    {{
      "action": "adjust_deadline|change_priority|add_resource|split_task",
      "task_id": 123,
      "details": "具体建议"
    }}
  ],
  "risk_score": 0-100
}}
"""
```

#### 3. Task_Modifier

**职责**: 任务修改器,解析自然语言并执行任务修改操作

**类定义**:

```python
# backend/app/services/task_modifier.py

from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import re

from app.models import Task
from app.services.llm_service import LLMService
from app.api.v1.tasks import tasksAPI

class TaskModifier:
    """任务修改器"""
    
    def __init__(self, db: AsyncSession, llm_service: LLMService):
        self.db = db
        self.llm_service = llm_service
    
    async def parse_modification_intent(
        self,
        user_input: str,
        context_tasks: List[Task]
    ) -> Dict[str, Any]:
        """解析修改意图"""
        pass
    
    async def execute_modification(
        self,
        modification: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行修改操作"""
        pass
    
    def _parse_relative_date(
        self,
        base_date: datetime,
        offset_str: str
    ) -> datetime:
        """解析相对日期 (如"延后3天")"""
        pass
    
    def _identify_tasks_by_description(
        self,
        description: str,
        tasks: List[Task]
    ) -> List[int]:
        """根据描述识别任务"""
        pass
```

**修改意图解析 Prompt**:

```python
MODIFICATION_PROMPT_TEMPLATE = """你是一个任务管理助手。用户想要修改任务,请解析用户意图。

用户输入: {user_input}

当前任务上下文:
{task_context}

请识别以下修改类型:
1. update_due_date: 修改截止日期
2. update_priority: 修改优先级
3. update_status: 修改状态
4. add_subtask: 添加子任务
5. update_description: 修改描述
6. batch_update: 批量修改

返回 JSON 格式:
{{
  "action": "update_due_date|update_priority|...",
  "task_ids": [123, 456],  // 受影响的任务ID
  "params": {{
    "due_date": "2024-12-31",  // 新截止日期
    "offset_days": 3,  // 相对偏移
    "priority": "high",  // 新优先级
    "status": "in_progress"  // 新状态
  }},
  "confirmation_message": "将任务 #123 的截止日期延后3天至 2024-12-31,是否确认?",
  "confidence": 0.9  // 置信度
}}
"""
```

#### 4. Project_Planner

**职责**: 项目规划器,分析任务结构并生成新任务建议

**类定义**:

```python
# backend/app/services/project_planner.py

from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Project, Task
from app.services.llm_service import LLMService

class ProjectPlanner:
    """项目规划器"""
    
    def __init__(self, db: AsyncSession, llm_service: LLMService):
        self.db = db
        self.llm_service = llm_service
    
    async def analyze_and_plan(
        self,
        project_id: int,
        user_id: int,
        planning_goal: Optional[str] = None
    ) -> Dict[str, Any]:
        """分析项目并生成规划建议"""
        pass
    
    async def _identify_missing_tasks(
        self,
        tasks: List[Task]
    ) -> List[str]:
        """识别缺失的任务类型"""
        pass
    
    async def _suggest_task_timeline(
        self,
        existing_tasks: List[Task],
        new_task: Dict
    ) -> Dict[str, str]:
        """建议新任务的时间安排"""
        pass
```


### 前端组件

#### 1. AIAssistantPanel (统一 AI 助手面板)

**职责**: 统一的 AI 对话界面,支持四种模式切换

**组件定义**:

```typescript
// frontend/src/components/ai/AIAssistantPanel.tsx

interface AIAssistantPanelProps {
  projectId: number;
  mode: 'create' | 'analyze' | 'modify' | 'plan';
  taskId?: number;  // 修改模式时需要
  open: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  actions?: Action[];  // 可执行操作
}

interface Action {
  type: 'apply_modification' | 'create_tasks' | 'view_analysis';
  label: string;
  data: any;
}

export default function AIAssistantPanel({
  projectId,
  mode,
  taskId,
  open,
  onClose,
  onSuccess
}: AIAssistantPanelProps) {
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  
  // 初始化对话
  useEffect(() => {
    if (open && !conversationId) {
      initConversation();
    }
  }, [open]);
  
  const initConversation = async () => {
    // 创建新对话
    const res = await conversationsAPI.create({
      project_id: projectId,
      conversation_type: mode,
      task_id: taskId
    });
    setConversationId(res.data.id);
    
    // 根据模式发送初始消息
    if (mode === 'analyze') {
      await sendMessage('请分析这个项目的任务情况');
    }
  };
  
  const sendMessage = async (content: string) => {
    // 发送消息逻辑
  };
  
  const handleAction = async (action: Action) => {
    // 执行操作逻辑
  };
  
  return (
    <Drawer
      title={getModeTitle(mode)}
      open={open}
      onClose={onClose}
      width={720}
    >
      {/* 对话历史列表按钮 */}
      <Button onClick={() => setHistoryOpen(true)}>
        历史对话
      </Button>
      
      {/* 消息列表 */}
      <div className="messages-container">
        {messages.map(msg => (
          <MessageBubble
            key={msg.id}
            message={msg}
            onAction={handleAction}
          />
        ))}
      </div>
      
      {/* 输入框 */}
      <div className="input-container">
        <TextArea
          value={inputValue}
          onChange={e => setInputValue(e.target.value)}
          onPressEnter={handleSend}
        />
        <Button onClick={handleSend} loading={loading}>
          发送
        </Button>
      </div>
      
      {/* 历史对话抽屉 */}
      <ConversationHistoryDrawer
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        onSelect={loadConversation}
      />
    </Drawer>
  );
}
```

#### 2. MessageBubble (消息气泡组件)

```typescript
// frontend/src/components/ai/MessageBubble.tsx

interface MessageBubbleProps {
  message: Message;
  onAction: (action: Action) => void;
}

export default function MessageBubble({ message, onAction }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  
  return (
    <div className={`message-bubble ${isUser ? 'user' : 'assistant'}`}>
      <div className="message-header">
        {isUser ? <UserOutlined /> : <RobotOutlined />}
        <span>{dayjs(message.timestamp).format('HH:mm')}</span>
      </div>
      
      <div className="message-content">
        {/* 支持 Markdown 渲染 */}
        <ReactMarkdown>{message.content}</ReactMarkdown>
      </div>
      
      {/* 操作按钮 */}
      {message.actions && message.actions.length > 0 && (
        <div className="message-actions">
          {message.actions.map((action, idx) => (
            <Button
              key={idx}
              type="primary"
              size="small"
              onClick={() => onAction(action)}
            >
              {action.label}
            </Button>
          ))}
        </div>
      )}
    </div>
  );
}
```

#### 3. ConversationHistoryDrawer (历史对话抽屉)

```typescript
// frontend/src/components/ai/ConversationHistoryDrawer.tsx

interface ConversationHistoryDrawerProps {
  open: boolean;
  onClose: () => void;
  onSelect: (conversationId: number) => void;
}

export default function ConversationHistoryDrawer({
  open,
  onClose,
  onSelect
}: ConversationHistoryDrawerProps) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(false);
  
  useEffect(() => {
    if (open) {
      fetchConversations();
    }
  }, [open]);
  
  const fetchConversations = async () => {
    setLoading(true);
    try {
      const res = await conversationsAPI.list();
      setConversations(res.data);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <Drawer
      title="历史对话"
      open={open}
      onClose={onClose}
      width={400}
    >
      <List
        loading={loading}
        dataSource={conversations}
        renderItem={conv => (
          <List.Item
            onClick={() => {
              onSelect(conv.id);
              onClose();
            }}
            style={{ cursor: 'pointer' }}
          >
            <List.Item.Meta
              title={getConversationTitle(conv)}
              description={
                <>
                  <Tag>{CONVERSATION_TYPE_LABELS[conv.conversation_type]}</Tag>
                  <span>{dayjs(conv.created_at).format('YYYY-MM-DD HH:mm')}</span>
                </>
              }
            />
          </List.Item>
        )}
      />
    </Drawer>
  );
}
```

### API 接口

#### 1. Conversations API (后端)

```python
# backend/app/api/v1/conversations.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.database import get_db
from app.models import User
from app.schemas import (
    ConversationCreate,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
    AnalyzeRequest,
    ModifyRequest,
    PlanRequest
)
from app.api.v1.auth import get_current_user
from app.services.ai_conversation_service import AIConversationService
from app.services.task_analyzer import TaskAnalyzer
from app.services.task_modifier import TaskModifier
from app.services.project_planner import ProjectPlanner

router = APIRouter()

@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    request: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建新对话"""
    pass

@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse)
async def send_message(
    conversation_id: int,
    request: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """发送消息"""
    pass

@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    project_id: Optional[int] = None,
    conversation_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取对话列表"""
    pass

@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取对话详情"""
    pass

@router.post("/conversations/{conversation_id}/analyze")
async def analyze_tasks(
    conversation_id: int,
    request: AnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """任务分析"""
    pass

@router.post("/conversations/{conversation_id}/modify")
async def modify_tasks(
    conversation_id: int,
    request: ModifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """任务修改"""
    pass

@router.post("/conversations/{conversation_id}/plan")
async def plan_project(
    conversation_id: int,
    request: PlanRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """项目规划"""
    pass

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除对话"""
    pass
```

#### 2. Conversations API (前端)

```typescript
// frontend/src/api/index.ts (新增部分)

export const conversationsAPI = {
  // 创建对话
  create: (data: {
    project_id: number;
    conversation_type: 'create' | 'analyze' | 'modify' | 'plan';
    task_id?: number;
  }) => api.post('/conversations', data),
  
  // 发送消息
  sendMessage: (conversationId: number, data: { content: string }) =>
    api.post(`/conversations/${conversationId}/messages`, data, { timeout: 60000 }),
  
  // 获取对话列表
  list: (params?: {
    project_id?: number;
    conversation_type?: string;
  }) => api.get('/conversations', { params }),
  
  // 获取对话详情
  get: (conversationId: number) =>
    api.get(`/conversations/${conversationId}`),
  
  // 任务分析
  analyze: (conversationId: number, data?: { focus_areas?: string[] }) =>
    api.post(`/conversations/${conversationId}/analyze`, data, { timeout: 60000 }),
  
  // 任务修改
  modify: (conversationId: number, data: { modification: any }) =>
    api.post(`/conversations/${conversationId}/modify`, data),
  
  // 项目规划
  plan: (conversationId: number, data?: { planning_goal?: string }) =>
    api.post(`/conversations/${conversationId}/plan`, data, { timeout: 60000 }),
  
  // 删除对话
  delete: (conversationId: number) =>
    api.delete(`/conversations/${conversationId}`)
};
```


## Data Models

### 数据库表设计

#### ai_conversations 表

```sql
CREATE TABLE ai_conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    project_id INTEGER NOT NULL,
    task_id INTEGER,  -- 可选,修改模式时关联的任务
    conversation_type VARCHAR(20) NOT NULL,  -- 'create' | 'analyze' | 'modify' | 'plan'
    title VARCHAR(255),  -- 对话标题 (自动生成或用户自定义)
    messages TEXT NOT NULL,  -- JSON 格式存储消息列表
    context_data TEXT,  -- JSON 格式存储上下文数据
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL
);

CREATE INDEX idx_ai_conversations_user ON ai_conversations(user_id);
CREATE INDEX idx_ai_conversations_project ON ai_conversations(project_id);
CREATE INDEX idx_ai_conversations_created ON ai_conversations(created_at);
```

**字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| user_id | INTEGER | 用户 ID |
| project_id | INTEGER | 项目 ID |
| task_id | INTEGER | 任务 ID (可选,修改模式时使用) |
| conversation_type | VARCHAR(20) | 对话类型: create/analyze/modify/plan |
| title | VARCHAR(255) | 对话标题 |
| messages | TEXT | 消息列表 (JSON 格式) |
| context_data | TEXT | 上下文数据 (JSON 格式) |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

**messages 字段 JSON 格式**:

```json
[
  {
    "role": "user",
    "content": "请分析这个项目的任务情况",
    "timestamp": "2024-01-15T10:30:00Z"
  },
  {
    "role": "assistant",
    "content": "我已经分析了您的项目...",
    "timestamp": "2024-01-15T10:30:05Z",
    "actions": [
      {
        "type": "view_analysis",
        "label": "查看详细分析",
        "data": { "analysis_id": "xxx" }
      }
    ]
  }
]
```

**context_data 字段 JSON 格式**:

```json
{
  "project_name": "TaskTree 开发",
  "task_count": 45,
  "completed_count": 20,
  "last_analysis": {
    "timestamp": "2024-01-15T10:30:00Z",
    "risk_score": 65
  },
  "referenced_tasks": [123, 456, 789]
}
```

### SQLAlchemy 模型

```python
# backend/app/models/__init__.py (新增部分)

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import json

class AIConversation(Base):
    """AI 对话表"""
    __tablename__ = 'ai_conversations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey('tasks.id', ondelete='SET NULL'), index=True)
    conversation_type = Column(String(20), nullable=False, comment="对话类型: create/analyze/modify/plan")
    title = Column(String(255), comment="对话标题")
    messages = Column(Text, nullable=False, comment="消息列表 (JSON)")
    context_data = Column(Text, comment="上下文数据 (JSON)")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # 关联关系
    user = relationship('User', backref='ai_conversations')
    project = relationship('Project', backref='ai_conversations')
    task = relationship('Task', backref='ai_conversations')
    
    @property
    def messages_list(self) -> list:
        """获取消息列表"""
        return json.loads(self.messages) if self.messages else []
    
    @messages_list.setter
    def messages_list(self, value: list):
        """设置消息列表"""
        self.messages = json.dumps(value, ensure_ascii=False)
    
    @property
    def context_dict(self) -> dict:
        """获取上下文数据"""
        return json.loads(self.context_data) if self.context_data else {}
    
    @context_dict.setter
    def context_dict(self, value: dict):
        """设置上下文数据"""
        self.context_data = json.dumps(value, ensure_ascii=False)
```

### Pydantic Schemas

```python
# backend/app/schemas/__init__.py (新增部分)

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class MessageSchema(BaseModel):
    """消息 Schema"""
    role: str = Field(..., description="角色: user/assistant")
    content: str = Field(..., description="消息内容")
    timestamp: str = Field(..., description="时间戳")
    actions: Optional[List[Dict[str, Any]]] = Field(None, description="可执行操作")

class ConversationCreate(BaseModel):
    """创建对话请求"""
    project_id: int = Field(..., description="项目 ID")
    conversation_type: str = Field(..., description="对话类型: create/analyze/modify/plan")
    task_id: Optional[int] = Field(None, description="任务 ID (修改模式)")
    initial_message: Optional[str] = Field(None, description="初始消息")

class ConversationResponse(BaseModel):
    """对话响应"""
    id: int
    user_id: int
    project_id: int
    task_id: Optional[int]
    conversation_type: str
    title: Optional[str]
    messages: List[MessageSchema]
    context_data: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class MessageCreate(BaseModel):
    """发送消息请求"""
    content: str = Field(..., description="消息内容")

class MessageResponse(BaseModel):
    """消息响应"""
    reply: str = Field(..., description="AI 回复")
    conversation_id: int = Field(..., description="对话 ID")
    message_count: int = Field(..., description="消息总数")
    actions: Optional[List[Dict[str, Any]]] = Field(None, description="可执行操作")

class AnalyzeRequest(BaseModel):
    """任务分析请求"""
    focus_areas: Optional[List[str]] = Field(None, description="关注领域")

class ModifyRequest(BaseModel):
    """任务修改请求"""
    modification: Dict[str, Any] = Field(..., description="修改操作")

class PlanRequest(BaseModel):
    """项目规划请求"""
    planning_goal: Optional[str] = Field(None, description="规划目标")
```

### TypeScript 类型定义

```typescript
// frontend/src/types/index.ts (新增部分)

export interface Conversation {
  id: number;
  user_id: number;
  project_id: number;
  task_id?: number;
  conversation_type: 'create' | 'analyze' | 'modify' | 'plan';
  title?: string;
  messages: Message[];
  context_data?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  actions?: Action[];
}

export interface Action {
  type: 'apply_modification' | 'create_tasks' | 'view_analysis';
  label: string;
  data: any;
}

export const CONVERSATION_TYPE_LABELS: Record<string, string> = {
  create: '任务创建',
  analyze: '任务分析',
  modify: '任务修改',
  plan: '项目规划'
};
```


## Error Handling

### 错误分类和处理策略

#### 1. LLM API 错误

**错误类型**:
- 超时错误 (Timeout)
- 认证错误 (401/403)
- 速率限制 (429)
- 服务不可用 (500/503)

**处理策略**:

```python
# backend/app/services/ai_conversation_service.py

class LLMError(Exception):
    """LLM 调用错误基类"""
    pass

class LLMTimeoutError(LLMError):
    """LLM 超时错误"""
    pass

class LLMAuthError(LLMError):
    """LLM 认证错误"""
    pass

class LLMRateLimitError(LLMError):
    """LLM 速率限制错误"""
    pass

async def _call_llm_with_retry(
    self,
    messages: List[Dict],
    max_retries: int = 3
) -> str:
    """带重试的 LLM 调用"""
    
    for attempt in range(max_retries):
        try:
            response = await self.llm_service.chat(
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )
            return response
            
        except asyncio.TimeoutError:
            if attempt == max_retries - 1:
                raise LLMTimeoutError("LLM 服务响应超时,请稍后重试")
            await asyncio.sleep(2 ** attempt)  # 指数退避
            
        except Exception as e:
            error_msg = str(e)
            
            if "401" in error_msg or "403" in error_msg:
                raise LLMAuthError("API Key 无效或已过期,请检查配置")
            
            elif "429" in error_msg:
                if attempt == max_retries - 1:
                    raise LLMRateLimitError("API 调用频率超限,请稍后重试")
                await asyncio.sleep(5 * (attempt + 1))
            
            elif "500" in error_msg or "503" in error_msg:
                if attempt == max_retries - 1:
                    raise LLMError(f"LLM 服务暂时不可用: {error_msg}")
                await asyncio.sleep(3 ** attempt)
            
            else:
                raise LLMError(f"LLM 调用失败: {error_msg}")
```

**前端错误处理**:

```typescript
// frontend/src/components/ai/AIAssistantPanel.tsx

const handleSendMessage = async (content: string) => {
  setLoading(true);
  try {
    const res = await conversationsAPI.sendMessage(conversationId, { content });
    // 处理成功响应
  } catch (error: any) {
    let errorMsg = 'AI 对话失败';
    
    if (error.response?.status === 504) {
      errorMsg = 'AI 响应超时,请稍后重试';
    } else if (error.response?.status === 400) {
      errorMsg = error.response.data?.detail || '未配置大模型服务';
    } else if (error.response?.status === 429) {
      errorMsg = 'API 调用频率超限,请稍后重试';
    } else if (error.message) {
      errorMsg = error.message;
    }
    
    message.error(errorMsg, 5);
  } finally {
    setLoading(false);
  }
};
```

#### 2. 权限错误

**错误类型**:
- 用户无权访问对话
- 用户无权访问项目
- 用户无权修改任务

**处理策略**:

```python
# backend/app/services/ai_conversation_service.py

async def verify_conversation_access(
    self,
    conversation_id: int,
    user_id: int
) -> AIConversation:
    """验证对话访问权限"""
    
    result = await self.db.execute(
        select(AIConversation).where(
            and_(
                AIConversation.id == conversation_id,
                AIConversation.user_id == user_id
            )
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="对话不存在或您无权访问"
        )
    
    return conversation

async def verify_project_access(
    self,
    project_id: int,
    user_id: int
) -> Project:
    """验证项目访问权限"""
    
    result = await self.db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    # 检查是否是项目所有者或成员
    if project.owner_id != user_id:
        result = await self.db.execute(
            select(ProjectMember).where(
                and_(
                    ProjectMember.project_id == project_id,
                    ProjectMember.user_id == user_id
                )
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="您无权访问该项目")
    
    return project
```

#### 3. 数据验证错误

**错误类型**:
- 对话类型无效
- 消息内容为空
- 修改操作格式错误

**处理策略**:

```python
# backend/app/api/v1/conversations.py

VALID_CONVERSATION_TYPES = ['create', 'analyze', 'modify', 'plan']

@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    request: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建新对话"""
    
    # 验证对话类型
    if request.conversation_type not in VALID_CONVERSATION_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"无效的对话类型,支持的类型: {', '.join(VALID_CONVERSATION_TYPES)}"
        )
    
    # 验证项目访问权限
    service = AIConversationService(db, llm_service)
    await service.verify_project_access(request.project_id, current_user.id)
    
    # 创建对话
    conversation = await service.create_conversation(
        user_id=current_user.id,
        project_id=request.project_id,
        conversation_type=request.conversation_type,
        initial_message=request.initial_message
    )
    
    return conversation
```

#### 4. 任务修改错误

**错误类型**:
- 任务不存在
- 修改操作失败
- 批量修改部分失败

**处理策略**:

```python
# backend/app/services/task_modifier.py

async def execute_modification(
    self,
    modification: Dict[str, Any]
) -> Dict[str, Any]:
    """执行修改操作"""
    
    action = modification.get('action')
    task_ids = modification.get('task_ids', [])
    params = modification.get('params', {})
    
    results = {
        'success': [],
        'failed': [],
        'errors': []
    }
    
    for task_id in task_ids:
        try:
            # 验证任务存在
            result = await self.db.execute(
                select(Task).where(Task.id == task_id)
            )
            task = result.scalar_one_or_none()
            
            if not task:
                results['failed'].append(task_id)
                results['errors'].append(f"任务 #{task_id} 不存在")
                continue
            
            # 执行修改
            if action == 'update_due_date':
                new_due_date = params.get('due_date')
                await self.db.execute(
                    update(Task)
                    .where(Task.id == task_id)
                    .values(due_date=new_due_date)
                )
                results['success'].append(task_id)
            
            # ... 其他修改类型
            
        except Exception as e:
            results['failed'].append(task_id)
            results['errors'].append(f"任务 #{task_id} 修改失败: {str(e)}")
    
    await self.db.commit()
    
    return {
        'total': len(task_ids),
        'success_count': len(results['success']),
        'failed_count': len(results['failed']),
        'results': results
    }
```

### 用户友好的错误提示

**前端错误提示映射**:

```typescript
// frontend/src/utils/errorMessages.ts

export const ERROR_MESSAGES: Record<string, string> = {
  // LLM 错误
  'llm_timeout': 'AI 响应超时,请稍后重试',
  'llm_auth_error': 'API Key 无效,请在设置中重新配置',
  'llm_rate_limit': 'API 调用频率超限,请稍后重试',
  'llm_service_unavailable': 'AI 服务暂时不可用,请稍后重试',
  
  // 权限错误
  'conversation_not_found': '对话不存在或您无权访问',
  'project_access_denied': '您无权访问该项目',
  'task_access_denied': '您无权修改该任务',
  
  // 数据错误
  'invalid_conversation_type': '无效的对话类型',
  'empty_message': '消息内容不能为空',
  'invalid_modification': '修改操作格式错误',
  
  // 任务修改错误
  'task_not_found': '任务不存在',
  'modification_failed': '任务修改失败',
  'partial_modification_failed': '部分任务修改失败,请查看详情'
};

export function getErrorMessage(error: any): string {
  const errorCode = error.response?.data?.error_code;
  if (errorCode && ERROR_MESSAGES[errorCode]) {
    return ERROR_MESSAGES[errorCode];
  }
  
  const detail = error.response?.data?.detail;
  if (detail) {
    return detail;
  }
  
  return error.message || '操作失败,请稍后重试';
}
```


## Testing Strategy

### 测试层次

本功能采用三层测试策略:单元测试、集成测试和端到端测试。

#### 1. 单元测试

**后端单元测试**:

```python
# backend/tests/test_ai_conversation_service.py

import pytest
from datetime import datetime, timezone
from app.services.ai_conversation_service import AIConversationService
from app.models import AIConversation, User, Project

@pytest.mark.asyncio
async def test_create_conversation(db_session, test_user, test_project):
    """测试创建对话"""
    service = AIConversationService(db_session, mock_llm_service)
    
    conversation = await service.create_conversation(
        user_id=test_user.id,
        project_id=test_project.id,
        conversation_type='analyze'
    )
    
    assert conversation.id is not None
    assert conversation.user_id == test_user.id
    assert conversation.project_id == test_project.id
    assert conversation.conversation_type == 'analyze'
    assert len(conversation.messages_list) == 0

@pytest.mark.asyncio
async def test_add_message(db_session, test_conversation):
    """测试添加消息"""
    service = AIConversationService(db_session, mock_llm_service)
    
    await service.add_message(
        conversation_id=test_conversation.id,
        role='user',
        content='测试消息'
    )
    
    # 重新加载对话
    conversation = await service.get_conversation(
        test_conversation.id,
        test_conversation.user_id
    )
    
    assert len(conversation.messages_list) == 1
    assert conversation.messages_list[0]['role'] == 'user'
    assert conversation.messages_list[0]['content'] == '测试消息'

@pytest.mark.asyncio
async def test_compress_messages(db_session):
    """测试消息压缩"""
    service = AIConversationService(db_session, mock_llm_service)
    
    # 创建 35 条消息
    messages = [
        {'role': 'user' if i % 2 == 0 else 'assistant', 'content': f'消息 {i}'}
        for i in range(35)
    ]
    
    compressed = await service.compress_messages(messages)
    
    assert len(compressed) == 30
    assert compressed[0]['content'] == '消息 5'  # 最早的5条被移除

@pytest.mark.asyncio
async def test_verify_conversation_access_denied(db_session, test_conversation):
    """测试对话访问权限验证 - 拒绝"""
    service = AIConversationService(db_session, mock_llm_service)
    
    with pytest.raises(HTTPException) as exc_info:
        await service.verify_conversation_access(
            conversation_id=test_conversation.id,
            user_id=999  # 不存在的用户
        )
    
    assert exc_info.value.status_code == 404
```

```python
# backend/tests/test_task_analyzer.py

import pytest
from app.services.task_analyzer import TaskAnalyzer

@pytest.mark.asyncio
async def test_analyze_project_tasks(db_session, test_project, test_tasks):
    """测试项目任务分析"""
    analyzer = TaskAnalyzer(db_session, mock_llm_service)
    
    # Mock LLM 响应
    mock_llm_service.chat.return_value = json.dumps({
        'summary': '项目进展良好',
        'issues': [
            {
                'type': 'bottleneck',
                'severity': 'high',
                'task_ids': [1, 2],
                'description': '任务 #1 阻塞了任务 #2',
                'suggestion': '优先完成任务 #1'
            }
        ],
        'recommendations': [],
        'risk_score': 45
    })
    
    result = await analyzer.analyze_project_tasks(
        project_id=test_project.id,
        user_id=test_project.owner_id
    )
    
    assert result['summary'] == '项目进展良好'
    assert len(result['issues']) == 1
    assert result['issues'][0]['type'] == 'bottleneck'
    assert result['risk_score'] == 45

@pytest.mark.asyncio
async def test_parse_analysis_response_invalid_json(db_session):
    """测试解析无效 JSON 响应"""
    analyzer = TaskAnalyzer(db_session, mock_llm_service)
    
    with pytest.raises(ValueError):
        await analyzer._parse_analysis_response('这不是 JSON')
```

```python
# backend/tests/test_task_modifier.py

import pytest
from app.services.task_modifier import TaskModifier

@pytest.mark.asyncio
async def test_parse_modification_intent_update_due_date(db_session):
    """测试解析修改意图 - 更新截止日期"""
    modifier = TaskModifier(db_session, mock_llm_service)
    
    # Mock LLM 响应
    mock_llm_service.chat.return_value = json.dumps({
        'action': 'update_due_date',
        'task_ids': [123],
        'params': {
            'offset_days': 3
        },
        'confirmation_message': '将任务 #123 的截止日期延后3天,是否确认?',
        'confidence': 0.95
    })
    
    result = await modifier.parse_modification_intent(
        user_input='把这个任务延后3天',
        context_tasks=[mock_task_123]
    )
    
    assert result['action'] == 'update_due_date'
    assert result['task_ids'] == [123]
    assert result['params']['offset_days'] == 3
    assert result['confidence'] == 0.95

@pytest.mark.asyncio
async def test_execute_modification_batch(db_session, test_tasks):
    """测试批量修改执行"""
    modifier = TaskModifier(db_session, mock_llm_service)
    
    modification = {
        'action': 'update_priority',
        'task_ids': [1, 2, 3],
        'params': {
            'priority': 'high'
        }
    }
    
    result = await modifier.execute_modification(modification)
    
    assert result['total'] == 3
    assert result['success_count'] == 3
    assert result['failed_count'] == 0
```

**前端单元测试**:

```typescript
// frontend/src/components/ai/__tests__/AIAssistantPanel.test.tsx

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import AIAssistantPanel from '../AIAssistantPanel';
import { conversationsAPI } from '../../../api';

jest.mock('../../../api');

describe('AIAssistantPanel', () => {
  it('should create conversation on open', async () => {
    const mockCreate = jest.fn().mockResolvedValue({
      code: 200,
      data: { id: 1, messages: [] }
    });
    (conversationsAPI.create as jest.Mock) = mockCreate;
    
    render(
      <AIAssistantPanel
        projectId={1}
        mode="analyze"
        open={true}
        onClose={() => {}}
      />
    );
    
    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith({
        project_id: 1,
        conversation_type: 'analyze'
      });
    });
  });
  
  it('should send message and display response', async () => {
    const mockSendMessage = jest.fn().mockResolvedValue({
      code: 200,
      data: {
        reply: 'AI 回复内容',
        conversation_id: 1,
        message_count: 2
      }
    });
    (conversationsAPI.sendMessage as jest.Mock) = mockSendMessage;
    
    render(
      <AIAssistantPanel
        projectId={1}
        mode="analyze"
        open={true}
        onClose={() => {}}
      />
    );
    
    const input = screen.getByPlaceholderText(/输入消息/i);
    const sendButton = screen.getByText(/发送/i);
    
    fireEvent.change(input, { target: { value: '测试消息' } });
    fireEvent.click(sendButton);
    
    await waitFor(() => {
      expect(mockSendMessage).toHaveBeenCalledWith(1, { content: '测试消息' });
      expect(screen.getByText('AI 回复内容')).toBeInTheDocument();
    });
  });
  
  it('should handle error gracefully', async () => {
    const mockSendMessage = jest.fn().mockRejectedValue({
      response: { status: 504 }
    });
    (conversationsAPI.sendMessage as jest.Mock) = mockSendMessage;
    
    render(
      <AIAssistantPanel
        projectId={1}
        mode="analyze"
        open={true}
        onClose={() => {}}
      />
    );
    
    const input = screen.getByPlaceholderText(/输入消息/i);
    const sendButton = screen.getByText(/发送/i);
    
    fireEvent.change(input, { target: { value: '测试消息' } });
    fireEvent.click(sendButton);
    
    await waitFor(() => {
      expect(screen.getByText(/AI 响应超时/i)).toBeInTheDocument();
    });
  });
});
```

#### 2. 集成测试

**后端集成测试**:

```python
# backend/tests/test_conversations_api.py

import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_conversation_api(client: AsyncClient, auth_headers, test_project):
    """测试创建对话 API"""
    response = await client.post(
        '/api/v1/conversations',
        headers=auth_headers,
        json={
            'project_id': test_project.id,
            'conversation_type': 'analyze'
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data['code'] == 200
    assert data['data']['conversation_type'] == 'analyze'
    assert data['data']['project_id'] == test_project.id

@pytest.mark.asyncio
async def test_send_message_api(client: AsyncClient, auth_headers, test_conversation):
    """测试发送消息 API"""
    response = await client.post(
        f'/api/v1/conversations/{test_conversation.id}/messages',
        headers=auth_headers,
        json={
            'content': '请分析任务'
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data['code'] == 200
    assert 'reply' in data['data']
    assert data['data']['conversation_id'] == test_conversation.id

@pytest.mark.asyncio
async def test_analyze_tasks_api(client: AsyncClient, auth_headers, test_conversation):
    """测试任务分析 API"""
    response = await client.post(
        f'/api/v1/conversations/{test_conversation.id}/analyze',
        headers=auth_headers,
        json={
            'focus_areas': ['bottleneck', 'risk']
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data['code'] == 200
    assert 'summary' in data['data']
    assert 'issues' in data['data']

@pytest.mark.asyncio
async def test_conversation_access_denied(client: AsyncClient, auth_headers):
    """测试对话访问权限拒绝"""
    response = await client.get(
        '/api/v1/conversations/999',  # 不存在的对话
        headers=auth_headers
    )
    
    assert response.status_code == 404
```

#### 3. 端到端测试

**E2E 测试场景**:

```typescript
// frontend/e2e/ai-conversation.spec.ts

import { test, expect } from '@playwright/test';

test.describe('AI Conversation Memory', () => {
  test.beforeEach(async ({ page }) => {
    // 登录
    await page.goto('/login');
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'password');
    await page.click('button[type="submit"]');
    
    // 进入项目详情页
    await page.goto('/projects/1');
  });
  
  test('should analyze project tasks', async ({ page }) => {
    // 点击 "AI 分析" 按钮
    await page.click('button:has-text("AI 分析")');
    
    // 等待 AI 助手面板打开
    await expect(page.locator('.ai-assistant-panel')).toBeVisible();
    
    // 等待分析结果
    await expect(page.locator('.message-bubble.assistant')).toBeVisible({ timeout: 60000 });
    
    // 验证分析结果包含关键信息
    const analysisText = await page.locator('.message-bubble.assistant').textContent();
    expect(analysisText).toContain('分析');
  });
  
  test('should modify task via natural language', async ({ page }) => {
    // 打开任务详情
    await page.click('.task-item:first-child');
    
    // 点击 "AI 修改" 按钮
    await page.click('button:has-text("AI 修改")');
    
    // 输入修改指令
    await page.fill('textarea[placeholder*="输入"]', '把这个任务延后3天');
    await page.click('button:has-text("发送")');
    
    // 等待 AI 回复
    await expect(page.locator('.message-bubble.assistant')).toBeVisible({ timeout: 60000 });
    
    // 点击确认按钮
    await page.click('button:has-text("确认修改")');
    
    // 验证修改成功提示
    await expect(page.locator('.ant-message-success')).toBeVisible();
  });
  
  test('should continue conversation with context', async ({ page }) => {
    // 打开 AI 助手
    await page.click('button:has-text("AI 分析")');
    
    // 发送第一条消息
    await page.fill('textarea', '分析任务进度');
    await page.click('button:has-text("发送")');
    await expect(page.locator('.message-bubble.assistant')).toBeVisible({ timeout: 60000 });
    
    // 发送第二条消息 (引用上下文)
    await page.fill('textarea', '刚才提到的瓶颈任务是哪个?');
    await page.click('button:has-text("发送")');
    await expect(page.locator('.message-bubble.assistant').nth(1)).toBeVisible({ timeout: 60000 });
    
    // 验证 AI 能理解上下文
    const secondResponse = await page.locator('.message-bubble.assistant').nth(1).textContent();
    expect(secondResponse).toContain('任务');
  });
  
  test('should load conversation history', async ({ page }) => {
    // 打开 AI 助手
    await page.click('button:has-text("AI 分析")');
    
    // 点击历史对话按钮
    await page.click('button:has-text("历史对话")');
    
    // 验证历史对话列表
    await expect(page.locator('.conversation-history-drawer')).toBeVisible();
    await expect(page.locator('.conversation-item')).toHaveCount(1, { timeout: 5000 });
    
    // 选择一个历史对话
    await page.click('.conversation-item:first-child');
    
    // 验证对话内容加载
    await expect(page.locator('.message-bubble')).toHaveCount(2, { timeout: 5000 });
  });
});
```

### 性能测试

**负载测试**:

```python
# backend/tests/performance/test_conversation_load.py

import asyncio
import pytest
from locust import HttpUser, task, between

class ConversationUser(HttpUser):
    """对话负载测试用户"""
    wait_time = between(1, 3)
    
    def on_start(self):
        """登录并创建对话"""
        response = self.client.post('/api/v1/auth/login', json={
            'email': 'test@example.com',
            'password': 'password'
        })
        self.token = response.json()['data']['token']
        self.headers = {'Authorization': f'Bearer {self.token}'}
        
        # 创建对话
        response = self.client.post(
            '/api/v1/conversations',
            headers=self.headers,
            json={
                'project_id': 1,
                'conversation_type': 'analyze'
            }
        )
        self.conversation_id = response.json()['data']['id']
    
    @task(3)
    def send_message(self):
        """发送消息"""
        self.client.post(
            f'/api/v1/conversations/{self.conversation_id}/messages',
            headers=self.headers,
            json={'content': '分析任务进度'},
            timeout=60
        )
    
    @task(1)
    def list_conversations(self):
        """获取对话列表"""
        self.client.get(
            '/api/v1/conversations',
            headers=self.headers
        )

# 运行: locust -f test_conversation_load.py --host=http://localhost:8000
```

### 测试覆盖率目标

- **后端代码覆盖率**: ≥ 80%
- **前端组件覆盖率**: ≥ 70%
- **API 端点覆盖率**: 100%
- **关键路径覆盖率**: 100%


### Property-Based Testing 适用性评估

本功能**不适合**使用 Property-Based Testing (PBT),原因如下:

1. **外部服务依赖**: 核心功能依赖 LLM API 调用,这是外部服务行为,不适合 PBT
2. **非确定性输出**: LLM 响应具有随机性,相同输入可能产生不同输出,无法定义稳定的属性
3. **副作用操作**: 对话历史存储、任务修改等都是副作用操作,不是纯函数
4. **集成测试更合适**: 本功能更适合使用 Mock-based 单元测试和集成测试

**替代测试策略**:
- 使用 Mock LLM Service 进行单元测试
- 使用真实 LLM API 进行集成测试 (少量示例)
- 使用 E2E 测试验证完整用户流程
- 使用负载测试验证性能和稳定性

因此,本设计文档**不包含 Correctness Properties 部分**。


## 关键技术决策

### 1. 对话历史存储格式

**决策**: 使用 JSON 格式存储在 TEXT 字段中

**理由**:
- SQLite 原生支持 JSON 函数,可以直接查询和操作
- 灵活性高,可以轻松扩展消息结构
- 避免创建额外的消息表,简化数据库设计
- 对话历史通常作为整体加载,不需要单独查询单条消息

**权衡**:
- 优点: 简单、灵活、易于扩展
- 缺点: 无法对单条消息建立索引,但对话历史查询场景不需要

**实现细节**:
```python
# 使用 SQLAlchemy 的 property 封装 JSON 序列化
@property
def messages_list(self) -> list:
    return json.loads(self.messages) if self.messages else []

@messages_list.setter
def messages_list(self, value: list):
    self.messages = json.dumps(value, ensure_ascii=False)
```

### 2. 上下文管理策略

**决策**: 保留最近 30 条消息 (15 轮对话)

**理由**:
- 平衡上下文完整性和 token 消耗
- 15 轮对话足够覆盖大多数任务分析和修改场景
- 避免超过 LLM 的 context window 限制 (通常 4K-8K tokens)

**实现策略**:
```python
MAX_MESSAGES = 30
MAX_CONTEXT_TOKENS = 4000

async def compress_messages(self, messages: List[Dict]) -> List[Dict]:
    """压缩消息历史"""
    if len(messages) <= self.MAX_MESSAGES:
        return messages
    
    # 保留最近 30 条
    compressed = messages[-self.MAX_MESSAGES:]
    
    # 如果仍然超过 token 限制,进一步压缩
    total_tokens = self._estimate_tokens(compressed)
    if total_tokens > self.MAX_CONTEXT_TOKENS:
        # 保留 system prompt + 最近 20 条
        compressed = compressed[-20:]
    
    return compressed
```

### 3. LLM API 调用优化

**决策**: 实现重试机制和速率限制

**重试策略**:
- 最多重试 3 次
- 使用指数退避 (2^attempt 秒)
- 超时错误和 5xx 错误重试,4xx 错误不重试

**速率限制**:
- 每个用户每分钟最多 20 次 LLM 调用
- 使用 Redis 或内存缓存实现计数器
- 超限返回 429 错误

**实现**:
```python
from functools import wraps
from collections import defaultdict
from datetime import datetime, timedelta

# 简单的内存速率限制器
rate_limiter = defaultdict(list)

def rate_limit(max_calls: int, window_seconds: int):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            user_id = kwargs.get('user_id') or args[0]
            now = datetime.now()
            
            # 清理过期记录
            rate_limiter[user_id] = [
                t for t in rate_limiter[user_id]
                if now - t < timedelta(seconds=window_seconds)
            ]
            
            # 检查速率限制
            if len(rate_limiter[user_id]) >= max_calls:
                raise LLMRateLimitError("API 调用频率超限")
            
            # 记录本次调用
            rate_limiter[user_id].append(now)
            
            return await func(self, *args, **kwargs)
        return wrapper
    return decorator

@rate_limit(max_calls=20, window_seconds=60)
async def send_message(self, conversation_id: int, user_message: str, user_id: int):
    # ... 实现
```

### 4. 错误处理机制

**决策**: 分层错误处理 + 用户友好提示

**错误分层**:
1. **LLM 层**: 捕获 API 错误,转换为自定义异常
2. **Service 层**: 处理业务逻辑错误,返回结构化错误信息
3. **API 层**: 统一错误响应格式,返回 HTTP 状态码
4. **Frontend 层**: 展示用户友好的错误提示

**错误响应格式**:
```json
{
  "code": 400,
  "message": "操作失败",
  "error_code": "llm_timeout",
  "detail": "AI 响应超时,请稍后重试",
  "data": null
}
```

### 5. 前端状态管理

**决策**: 使用组件内部状态 + API 调用,不使用全局状态管理

**理由**:
- 对话状态是临时的,不需要跨组件共享
- 对话历史从服务器加载,不需要客户端缓存
- 简化实现,避免引入额外的状态管理复杂度

**实现**:
```typescript
// 组件内部状态
const [conversationId, setConversationId] = useState<number | null>(null);
const [messages, setMessages] = useState<Message[]>([]);
const [loading, setLoading] = useState(false);

// 直接调用 API,不使用全局 store
const sendMessage = async (content: string) => {
  setLoading(true);
  try {
    const res = await conversationsAPI.sendMessage(conversationId, { content });
    setMessages([...messages, { role: 'user', content }, { role: 'assistant', content: res.data.reply }]);
  } finally {
    setLoading(false);
  }
};
```

### 6. 集成点设计

**决策**: 最小化侵入,通过按钮触发 AI 助手面板

**集成位置**:
1. **ProjectDetail 页面**: 添加 "AI 分析" 按钮
2. **TaskDetailDrawer**: 添加 "AI 修改" 按钮
3. **AITaskCreatorModal**: 扩展支持对话历史

**实现**:
```typescript
// ProjectDetail.tsx
<Button
  type="primary"
  icon={<RobotOutlined />}
  onClick={() => {
    setAiMode('analyze');
    setAiPanelOpen(true);
  }}
>
  AI 分析
</Button>

<AIAssistantPanel
  projectId={Number(id)}
  mode={aiMode}
  open={aiPanelOpen}
  onClose={() => setAiPanelOpen(false)}
  onSuccess={() => {
    fetchTasks();
    fetchProject();
  }}
/>
```

### 7. 数据库迁移策略

**决策**: 使用 Alembic 进行数据库迁移

**迁移脚本**:
```python
# backend/alembic/versions/xxx_add_ai_conversations.py

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'ai_conversations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=True),
        sa.Column('conversation_type', sa.String(20), nullable=False),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('messages', sa.Text(), nullable=False),
        sa.Column('context_data', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='SET NULL')
    )
    
    op.create_index('idx_ai_conversations_user', 'ai_conversations', ['user_id'])
    op.create_index('idx_ai_conversations_project', 'ai_conversations', ['project_id'])
    op.create_index('idx_ai_conversations_created', 'ai_conversations', ['created_at'])

def downgrade():
    op.drop_index('idx_ai_conversations_created', 'ai_conversations')
    op.drop_index('idx_ai_conversations_project', 'ai_conversations')
    op.drop_index('idx_ai_conversations_user', 'ai_conversations')
    op.drop_table('ai_conversations')
```

## 性能和资源管理

### 1. 对话数量限制

**策略**: 每个用户最多保留 10 个活跃对话

**实现**:
```python
async def create_conversation(self, user_id: int, project_id: int, conversation_type: str):
    # 检查用户对话数量
    result = await self.db.execute(
        select(func.count(AIConversation.id))
        .where(AIConversation.user_id == user_id)
    )
    count = result.scalar()
    
    if count >= 10:
        # 删除最旧的对话
        oldest = await self.db.execute(
            select(AIConversation)
            .where(AIConversation.user_id == user_id)
            .order_by(AIConversation.updated_at.asc())
            .limit(1)
        )
        await self.db.delete(oldest.scalar_one())
    
    # 创建新对话
    # ...
```

### 2. 自动清理策略

**策略**: 定期清理 30 天前的对话历史

**实现**:
```python
# backend/app/tasks/cleanup.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta, timezone

async def cleanup_old_conversations():
    """清理 30 天前的对话"""
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
    
    async with get_db() as db:
        result = await db.execute(
            delete(AIConversation)
            .where(AIConversation.updated_at < cutoff_date)
        )
        deleted_count = result.rowcount
        await db.commit()
        
        print(f"Cleaned up {deleted_count} old conversations")

# 每天凌晨 2 点执行
scheduler = AsyncIOScheduler()
scheduler.add_job(cleanup_old_conversations, 'cron', hour=2)
scheduler.start()
```

### 3. 对话记录大小限制

**策略**: 单条对话记录不超过 100KB

**实现**:
```python
async def add_message(self, conversation_id: int, role: str, content: str):
    conversation = await self.get_conversation(conversation_id)
    
    # 添加新消息
    messages = conversation.messages_list
    messages.append({
        'role': role,
        'content': content,
        'timestamp': datetime.now(timezone.utc).isoformat()
    })
    
    # 检查大小
    messages_json = json.dumps(messages, ensure_ascii=False)
    if len(messages_json.encode('utf-8')) > 100 * 1024:  # 100KB
        # 移除最早的消息
        messages = messages[1:]
    
    conversation.messages_list = messages
    await self.db.commit()
```

### 4. LLM API 超时设置

**策略**: 60 秒超时,避免长时间阻塞

**实现**:
```python
# backend/app/services/llm_service.py

async def chat(self, messages: list, temperature: float = 0.7, max_tokens: int = 2000) -> str:
    """通用对话接口"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            # ...
    except httpx.TimeoutException:
        raise LLMTimeoutError("LLM 服务响应超时")
```

## 安全和权限控制

### 1. 对话访问权限验证

**策略**: 用户只能访问自己创建的对话

**实现**:
```python
async def verify_conversation_access(self, conversation_id: int, user_id: int):
    result = await self.db.execute(
        select(AIConversation).where(
            and_(
                AIConversation.id == conversation_id,
                AIConversation.user_id == user_id
            )
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在或您无权访问")
    
    return conversation
```

### 2. 项目权限验证

**策略**: 验证用户对项目的访问权限

**实现**:
```python
async def verify_project_access(self, project_id: int, user_id: int):
    # 检查是否是项目所有者
    result = await self.db.execute(
        select(Project).where(
            and_(
                Project.id == project_id,
                Project.owner_id == user_id
            )
        )
    )
    project = result.scalar_one_or_none()
    
    if project:
        return project
    
    # 检查是否是项目成员
    result = await self.db.execute(
        select(ProjectMember).where(
            and_(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id
            )
        )
    )
    member = result.scalar_one_or_none()
    
    if not member:
        raise HTTPException(status_code=403, detail="您无权访问该项目")
    
    # 返回项目
    result = await self.db.execute(
        select(Project).where(Project.id == project_id)
    )
    return result.scalar_one()
```

### 3. 敏感信息过滤

**策略**: 在对话上下文中过滤敏感信息

**实现**:
```python
async def build_context(self, conversation: AIConversation) -> Dict[str, Any]:
    """构建对话上下文"""
    # 获取项目信息
    project = await self.db.get(Project, conversation.project_id)
    
    # 获取任务数据 (过滤敏感字段)
    tasks = await self._get_project_tasks(conversation.project_id)
    
    # 构建上下文 (不包含用户邮箱、密码等敏感信息)
    context = {
        'project': {
            'id': project.id,
            'name': project.name,
            'description': project.description,
            # 不包含 owner_id 等敏感信息
        },
        'tasks': [
            {
                'id': task.id,
                'name': task.name,
                'status': task.status,
                'priority': task.priority,
                # 不包含 assignee 的详细信息
            }
            for task in tasks
        ]
    }
    
    return context
```

### 4. 审计日志

**策略**: 记录所有 AI 操作的审计日志

**实现**:
```python
async def log_ai_operation(
    self,
    user_id: int,
    operation: str,
    conversation_id: int,
    details: Dict[str, Any]
):
    """记录 AI 操作日志"""
    log = OperationLog(
        user_id=user_id,
        action=f"ai_{operation}",
        old_value=None,
        new_value=json.dumps({
            'conversation_id': conversation_id,
            'details': details
        }, ensure_ascii=False),
        created_at=datetime.now(timezone.utc)
    )
    self.db.add(log)
    await self.db.commit()
```

## 部署和监控

### 1. 环境变量配置

```bash
# .env
LLM_PROVIDER=minimax
LLM_API_KEY=your_api_key
LLM_MODEL=MiniMax-M2.7
LLM_TIMEOUT=60
AI_CONVERSATION_MAX_MESSAGES=30
AI_CONVERSATION_MAX_CONTEXT_TOKENS=4000
AI_CONVERSATION_RATE_LIMIT=20
```

### 2. 监控指标

**关键指标**:
- LLM API 调用成功率
- LLM API 平均响应时间
- 对话创建数量 (每日/每周)
- 消息发送数量 (每日/每周)
- 错误率 (按错误类型分类)
- 用户活跃度 (使用 AI 功能的用户比例)

**实现**:
```python
# backend/app/monitoring/metrics.py

from prometheus_client import Counter, Histogram

llm_calls_total = Counter(
    'llm_calls_total',
    'Total number of LLM API calls',
    ['provider', 'status']
)

llm_response_time = Histogram(
    'llm_response_time_seconds',
    'LLM API response time in seconds',
    ['provider']
)

conversations_created = Counter(
    'conversations_created_total',
    'Total number of conversations created',
    ['conversation_type']
)

messages_sent = Counter(
    'messages_sent_total',
    'Total number of messages sent',
    ['conversation_type']
)
```

### 3. 日志记录

**日志级别**:
- INFO: 对话创建、消息发送
- WARNING: 速率限制触发、消息压缩
- ERROR: LLM API 错误、权限错误

**实现**:
```python
import logging

logger = logging.getLogger(__name__)

async def send_message(self, conversation_id: int, user_message: str):
    logger.info(f"Sending message to conversation {conversation_id}")
    
    try:
        response = await self._call_llm_with_retry(messages)
        logger.info(f"LLM response received for conversation {conversation_id}")
        return response
    except LLMRateLimitError as e:
        logger.warning(f"Rate limit exceeded for conversation {conversation_id}: {e}")
        raise
    except Exception as e:
        logger.error(f"Error sending message to conversation {conversation_id}: {e}")
        raise
```

## 总结

本设计文档定义了 TaskTree 项目「AI 对话记忆功能」的完整技术方案,包括:

1. **架构设计**: 清晰的三层架构 (Frontend → Backend → Data)
2. **组件设计**: 详细的服务类和前端组件定义
3. **数据模型**: 完整的数据库表设计和 ORM 模型
4. **API 接口**: RESTful API 设计和请求/响应格式
5. **错误处理**: 分层错误处理和用户友好提示
6. **测试策略**: 单元测试、集成测试、E2E 测试
7. **技术决策**: 关键技术选型和实现细节
8. **性能优化**: 资源管理和速率限制
9. **安全控制**: 权限验证和敏感信息过滤
10. **部署监控**: 环境配置和监控指标

该设计方案充分复用了现有的 LLM_Service 和任务管理功能,通过最小化侵入的方式集成 AI 对话能力,为用户提供智能化的任务管理体验。

