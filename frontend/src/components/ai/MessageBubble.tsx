import React from 'react';
import { UserOutlined, RobotOutlined } from '@ant-design/icons';
import { Button } from 'antd';
import ReactMarkdown from 'react-markdown';
import dayjs from 'dayjs';
import type { Message, Action } from '../../types';

interface MessageBubbleProps {
  message: Message;
  onAction?: (action: Action) => void;
}

export default function MessageBubble({ message, onAction }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  return (
    <div
      style={{
        display: 'flex',
        gap: 10,
        marginBottom: 16,
        flexDirection: isUser ? 'row-reverse' : 'row',
        alignItems: 'flex-start',
        animation: 'fadeSlideUp 0.3s var(--ease-smooth)',
      }}
    >
      {/* 头像 */}
      <div
        style={{
          flexShrink: 0,
          width: 30,
          height: 30,
          borderRadius: '50%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: isUser ? 'rgba(255, 255, 255, 0.2)' : 'rgba(255, 255, 255, 0.1)',
          color: '#fff',
          fontSize: 13,
        }}
      >
        {isUser ? <UserOutlined /> : <RobotOutlined />}
      </div>

      {/* 消息内容 */}
      <div style={{ flex: 1, textAlign: isUser ? 'right' : 'left' }}>
        <div
          style={{
            display: 'inline-block',
            maxWidth: '82%',
            padding: '10px 14px',
            borderRadius: isUser ? '12px 12px 2px 12px' : '12px 12px 12px 2px',
            background: isUser ? 'rgba(255, 255, 255, 0.15)' : 'rgba(255, 255, 255, 0.05)',
            color: '#fff',
            fontSize: 13,
            lineHeight: 1.6,
            textAlign: 'left',
          }}
        >
          <div className="prose-bubble">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        </div>

        {/* 时间戳 */}
        <div style={{
          fontSize: 11,
          color: 'var(--color-ink-tertiary)',
          marginTop: 4,
          fontVariantNumeric: 'tabular-nums',
        }}>
          {dayjs(message.timestamp).format('HH:mm')}
        </div>

        {/* 操作按钮 */}
        {message.actions && message.actions.length > 0 && (
          <div style={{ marginTop: 8, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {message.actions.map((action, idx) => (
              <Button
                key={idx}
                size="small"
                onClick={() => onAction?.(action)}
                style={{
                  borderRadius: 'var(--radius-button)',
                  fontSize: 12,
                }}
              >
                {action.label}
              </Button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
