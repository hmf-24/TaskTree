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
      className={`flex gap-3 mb-4 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
      style={{ alignItems: 'flex-start' }}
    >
      {/* 头像 */}
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
          isUser ? 'bg-blue-500' : 'bg-gray-500'
        }`}
      >
        {isUser ? (
          <UserOutlined className="text-white" />
        ) : (
          <RobotOutlined className="text-white" />
        )}
      </div>

      {/* 消息内容 */}
      <div className={`flex-1 ${isUser ? 'text-right' : 'text-left'}`}>
        <div
          className={`inline-block max-w-[80%] p-3 rounded-lg ${
            isUser ? 'bg-blue-500 text-white' : 'bg-gray-100 text-gray-900'
          }`}
        >
          <div className="prose prose-sm max-w-none">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        </div>

        {/* 时间戳 */}
        <div className="text-xs text-gray-400 mt-1">
          {dayjs(message.timestamp).format('HH:mm')}
        </div>

        {/* 操作按钮 */}
        {message.actions && message.actions.length > 0 && (
          <div className="mt-2 flex gap-2 flex-wrap">
            {message.actions.map((action, idx) => (
              <Button
                key={idx}
                type="primary"
                size="small"
                onClick={() => onAction?.(action)}
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
