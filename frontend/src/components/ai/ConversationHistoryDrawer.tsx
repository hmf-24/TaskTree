import React, { useEffect, useState } from 'react';
import { Drawer, List, Tag, Spin, Empty, Typography, Space } from 'antd';
import { MessageOutlined, ClockCircleOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { conversationsAPI } from '../../api';
import { CONVERSATION_TYPE_LABELS, type Conversation } from '../../types';

const { Text, Paragraph } = Typography;

interface ConversationHistoryDrawerProps {
  open: boolean;
  onClose: () => void;
  onSelect: (conversationId: number) => void;
  projectId?: number;
  conversationType?: string;
}

export default function ConversationHistoryDrawer({
  open,
  onClose,
  onSelect,
  projectId,
  conversationType,
}: ConversationHistoryDrawerProps) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open) {
      fetchConversations();
    }
  }, [open, projectId, conversationType]);

  const fetchConversations = async () => {
    setLoading(true);
    try {
      const params: any = {};
      if (projectId) params.project_id = projectId;
      if (conversationType) params.conversation_type = conversationType;
      
      const res = await conversationsAPI.list(params);
      setConversations(res.data || []);
    } catch (error) {
      console.error('Failed to fetch conversations:', error);
    } finally {
      setLoading(false);
    }
  };

  const getConversationTitle = (conv: Conversation) => {
    if (conv.title) return conv.title;
    const typeLabel = CONVERSATION_TYPE_LABELS[conv.conversation_type] || conv.conversation_type;
    return `${typeLabel} - ${dayjs(conv.created_at).format('MM-DD HH:mm')}`;
  };

  const getConversationSummary = (conv: Conversation) => {
    // 获取第一条用户消息作为摘要
    const firstUserMessage = conv.messages?.find(msg => msg.role === 'user');
    if (firstUserMessage) {
      const content = firstUserMessage.content;
      return content.length > 60 ? content.substring(0, 60) + '...' : content;
    }
    return '暂无内容';
  };

  const getMessageCount = (conv: Conversation) => {
    return conv.messages?.length || 0;
  };

  const formatTimeRange = (conv: Conversation) => {
    const start = dayjs(conv.created_at);
    const end = dayjs(conv.updated_at);
    
    if (start.isSame(end, 'day')) {
      return `${start.format('MM-DD HH:mm')} - ${end.format('HH:mm')}`;
    } else {
      return `${start.format('MM-DD HH:mm')} - ${end.format('MM-DD HH:mm')}`;
    }
  };

  return (
    <Drawer title="历史对话" open={open} onClose={onClose} width={480}>
      <Spin spinning={loading}>
        {conversations.length === 0 && !loading ? (
          <Empty description="暂无历史对话" />
        ) : (
          <List
            dataSource={conversations}
            renderItem={(conv) => (
              <List.Item
                onClick={() => {
                  onSelect(conv.id);
                  onClose();
                }}
                style={{ 
                  cursor: 'pointer', 
                  padding: '16px',
                  borderRadius: '8px',
                  marginBottom: '8px',
                  transition: 'all 0.2s ease',
                  border: '1px solid transparent',
                }}
                onMouseEnter={(e) => { 
                  const target = e.currentTarget as HTMLElement;
                  target.style.background = 'var(--color-surface-hover)';
                  target.style.borderColor = 'var(--color-border-hover)';
                }}
                onMouseLeave={(e) => { 
                  const target = e.currentTarget as HTMLElement;
                  target.style.background = 'transparent';
                  target.style.borderColor = 'transparent';
                }}
              >
                <List.Item.Meta
                  title={
                    <div style={{ marginBottom: '8px' }}>
                      <Text strong style={{ fontSize: '14px' }}>
                        {getConversationTitle(conv)}
                      </Text>
                    </div>
                  }
                  description={
                    <Space direction="vertical" size={8} style={{ width: '100%' }}>
                      {/* 对话摘要 */}
                      <Paragraph 
                        ellipsis={{ rows: 2 }} 
                        style={{ 
                          margin: 0, 
                          color: 'var(--color-ink-secondary)',
                          fontSize: '13px',
                        }}
                      >
                        {getConversationSummary(conv)}
                      </Paragraph>
                      
                      {/* 元信息 */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                        <Tag color="blue" style={{ margin: 0 }}>
                          {CONVERSATION_TYPE_LABELS[conv.conversation_type]}
                        </Tag>
                        
                        <Space size={4} style={{ fontSize: '12px', color: 'var(--color-ink-tertiary)' }}>
                          <MessageOutlined />
                          <span>{getMessageCount(conv)} 条消息</span>
                        </Space>
                        
                        <Space size={4} style={{ fontSize: '12px', color: 'var(--color-ink-tertiary)' }}>
                          <ClockCircleOutlined />
                          <span>{formatTimeRange(conv)}</span>
                        </Space>
                      </div>
                    </Space>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Spin>
    </Drawer>
  );
}
