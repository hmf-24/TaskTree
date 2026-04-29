import React, { useState, useEffect, useRef } from 'react';
import { Drawer, Input, Button, message, Spin } from 'antd';
import { HistoryOutlined, SendOutlined } from '@ant-design/icons';
import { conversationsAPI } from '../../api';
import MessageBubble from './MessageBubble';
import ConversationHistoryDrawer from './ConversationHistoryDrawer';
import type { Message, Action } from '../../types';

const { TextArea } = Input;

interface AIAssistantPanelProps {
  projectId: number;
  mode: 'create' | 'analyze' | 'modify' | 'plan';
  taskId?: number;
  open: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

const MODE_TITLES: Record<string, string> = {
  create: 'AI 任务创建',
  analyze: 'AI 任务分析',
  modify: 'AI 任务修改',
  plan: 'AI 项目规划',
};

export default function AIAssistantPanel({
  projectId,
  mode,
  taskId,
  open,
  onClose,
  onSuccess,
}: AIAssistantPanelProps) {
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [initializing, setInitializing] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 自动滚动到最新消息
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // 初始化对话
  useEffect(() => {
    if (open && !conversationId) {
      initConversation();
    }
  }, [open, projectId, mode, taskId]);

  // 重置状态
  useEffect(() => {
    if (!open) {
      setConversationId(null);
      setMessages([]);
      setInputValue('');
    }
  }, [open]);

  const initConversation = async () => {
    setInitializing(true);
    try {
      const res = await conversationsAPI.create({
        project_id: projectId,
        conversation_type: mode,
        task_id: taskId,
      });
      setConversationId(res.data.id);

      // 根据模式发送初始消息
      if (mode === 'analyze') {
        await sendMessage('请分析这个项目的任务情况', res.data.id);
      }
    } catch (error: any) {
      message.error(getErrorMessage(error));
    } finally {
      setInitializing(false);
    }
  };

  const sendMessage = async (content: string, convId?: number) => {
    const targetConvId = convId || conversationId;
    if (!targetConvId) return;

    const userMessage: Message = {
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setLoading(true);

    try {
      const res = await conversationsAPI.sendMessage(targetConvId, { content });
      const assistantMessage: Message = {
        role: 'assistant',
        content: res.data.reply,
        timestamp: new Date().toISOString(),
        actions: res.data.actions,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error: any) {
      message.error(getErrorMessage(error), 5);
      // 移除用户消息
      setMessages((prev) => prev.slice(0, -1));
    } finally {
      setLoading(false);
    }
  };

  const handleSend = () => {
    if (!inputValue.trim() || loading) return;
    sendMessage(inputValue.trim());
  };

  const handleAction = async (action: Action) => {
    if (!conversationId) return;

    try {
      if (action.type === 'apply_modification') {
        await conversationsAPI.modify(conversationId, { modification: action.data });
        message.success('任务修改成功');
        onSuccess?.();
      } else if (action.type === 'create_tasks') {
        // 处理创建任务操作
        message.success('任务创建成功');
        onSuccess?.();
      } else if (action.type === 'view_analysis') {
        // 处理查看分析操作
        message.info('查看详细分析');
      }
    } catch (error: any) {
      message.error(getErrorMessage(error));
    }
  };

  const loadConversation = async (convId: number) => {
    try {
      const res = await conversationsAPI.get(convId);
      setConversationId(res.data.id);
      setMessages(res.data.messages || []);
    } catch (error: any) {
      message.error(getErrorMessage(error));
    }
  };

  const getErrorMessage = (error: any): string => {
    if (error.response?.status === 504 || error.code === 'ECONNABORTED') {
      return 'AI 响应超时,请稍后重试';
    } else if (error.response?.status === 400) {
      return error.response.data?.detail || '未配置大模型服务';
    } else if (error.response?.status === 429) {
      return 'API 调用频率超限,请稍后重试';
    } else if (error.response?.data?.detail) {
      return error.response.data.detail;
    }
    return error.message || 'AI 对话失败';
  };

  return (
    <>
      <Drawer
        title={
          <div className="flex items-center justify-between">
            <span>{MODE_TITLES[mode]}</span>
            <Button
              type="text"
              icon={<HistoryOutlined />}
              onClick={() => setHistoryOpen(true)}
            >
              历史对话
            </Button>
          </div>
        }
        open={open}
        onClose={onClose}
        width={720}
        styles={{ body: { padding: 0, display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--color-canvas)' } }}
      >
        {initializing ? (
          <div className="flex items-center justify-center h-full">
            <Spin tip="正在初始化对话..." />
          </div>
        ) : (
          <>
            {/* 消息列表 */}
            <div className="flex-1 overflow-y-auto p-4">
              {messages.map((msg, idx) => (
                <MessageBubble key={idx} message={msg} onAction={handleAction} />
              ))}
              {loading && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--color-ink-tertiary)', fontSize: 13 }}>
                  <Spin size="small" />
                  <span>AI 正在思考…</span>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* 输入框 */}
            <div style={{
              borderTop: '1px solid var(--color-border)',
              padding: 16,
              background: 'var(--color-surface)',
            }}>
              <div className="flex gap-2">
                <TextArea
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onPressEnter={(e) => {
                    if (!e.shiftKey) {
                      e.preventDefault();
                      handleSend();
                    }
                  }}
                  placeholder="输入消息... (Shift+Enter 换行)"
                  autoSize={{ minRows: 2, maxRows: 6 }}
                  disabled={loading}
                />
                <Button
                  type="primary"
                  icon={<SendOutlined />}
                  onClick={handleSend}
                  loading={loading}
                  disabled={!inputValue.trim()}
                >
                  发送
                </Button>
              </div>
            </div>
          </>
        )}
      </Drawer>

      {/* 历史对话抽屉 */}
      <ConversationHistoryDrawer
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        onSelect={loadConversation}
        projectId={projectId}
      />
    </>
  );
}
