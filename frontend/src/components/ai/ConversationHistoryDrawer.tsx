import React, { useEffect, useState } from 'react';
import { Drawer, List, Tag, Spin, Empty } from 'antd';
import dayjs from 'dayjs';
import { conversationsAPI } from '../../api';
import { CONVERSATION_TYPE_LABELS, type Conversation } from '../../types';

interface ConversationHistoryDrawerProps {
  open: boolean;
  onClose: () => void;
  onSelect: (conversationId: number) => void;
  projectId?: number;
}

export default function ConversationHistoryDrawer({
  open,
  onClose,
  onSelect,
  projectId,
}: ConversationHistoryDrawerProps) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open) {
      fetchConversations();
    }
  }, [open, projectId]);

  const fetchConversations = async () => {
    setLoading(true);
    try {
      const res = await conversationsAPI.list(
        projectId ? { project_id: projectId } : undefined
      );
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

  return (
    <Drawer title="历史对话" open={open} onClose={onClose} width={400}>
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
                style={{ cursor: 'pointer' }}
                className="hover:bg-gray-50"
              >
                <List.Item.Meta
                  title={getConversationTitle(conv)}
                  description={
                    <div className="flex items-center gap-2">
                      <Tag color="blue">
                        {CONVERSATION_TYPE_LABELS[conv.conversation_type]}
                      </Tag>
                      <span className="text-xs text-gray-400">
                        {dayjs(conv.created_at).format('YYYY-MM-DD HH:mm')}
                      </span>
                    </div>
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
