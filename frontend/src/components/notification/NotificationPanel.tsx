import { useState, useEffect, useCallback } from 'react';
import { Popover, Badge, List, Button, Empty, message, Tabs } from 'antd';
import { BellOutlined, CheckOutlined } from '@ant-design/icons';
import { notificationsAPI } from '../../api';
import type { Notification } from '../../types';

export default function NotificationPanel() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);

  const fetchNotifications = useCallback(async () => {
    setLoading(true);
    try {
      const res = await notificationsAPI.list({ page_size: 20 });
      if (res.code === 200) {
        const items = res.data?.items || res.data || [];
        setNotifications(Array.isArray(items) ? items : []);
        setUnreadCount(Array.isArray(items) ? items.filter((n: Notification) => !n.is_read).length : 0);
      }
    } catch {
      // 静默处理，通知不是核心功能
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchNotifications();
    // 每60秒轮询一次
    const timer = setInterval(fetchNotifications, 60000);
    return () => clearInterval(timer);
  }, [fetchNotifications]);

  const handleMarkRead = async (id: number) => {
    try {
      await notificationsAPI.markRead(id);
      fetchNotifications();
    } catch (error: any) {
      message.error('操作失败');
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await notificationsAPI.markAllRead();
      fetchNotifications();
      message.success('已全部标记为已读');
    } catch (error: any) {
      message.error('操作失败');
    }
  };

  const typeIcon: Record<string, string> = {
    task_status: '📋',
    task_assign: '👤',
    comment: '💬',
    mention: '@',
  };

  const content = (
    <div style={{ width: 360 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid #f0f0f0' }}>
        <span style={{ fontWeight: 600 }}>通知</span>
        {unreadCount > 0 && (
          <Button type="link" size="small" onClick={handleMarkAllRead} icon={<CheckOutlined />}>
            全部已读
          </Button>
        )}
      </div>
      {notifications.length === 0 ? (
        <Empty description="暂无通知" image={Empty.PRESENTED_IMAGE_SIMPLE} style={{ padding: 24 }} />
      ) : (
        <List
          loading={loading}
          dataSource={notifications.slice(0, 10)}
          style={{ maxHeight: 400, overflow: 'auto' }}
          renderItem={(item: Notification) => (
            <List.Item
              style={{
                background: item.is_read ? 'transparent' : '#e6f7ff',
                padding: '8px 12px',
                cursor: item.is_read ? 'default' : 'pointer',
              }}
              onClick={() => !item.is_read && handleMarkRead(item.id)}
            >
              <List.Item.Meta
                avatar={<span style={{ fontSize: 18 }}>{typeIcon[item.type] || '🔔'}</span>}
                title={<span style={{ fontSize: 13 }}>{item.title || '系统通知'}</span>}
                description={
                  <div>
                    <div style={{ fontSize: 12, color: '#666' }}>{item.content}</div>
                    <div style={{ fontSize: 11, color: '#999', marginTop: 2 }}>
                      {new Date(item.created_at).toLocaleString('zh-CN')}
                    </div>
                  </div>
                }
              />
            </List.Item>
          )}
        />
      )}
    </div>
  );

  return (
    <Popover content={content} trigger="click" placement="bottomRight">
      <Badge count={unreadCount} size="small">
        <Button type="text" icon={<BellOutlined />} />
      </Badge>
    </Popover>
  );
}
