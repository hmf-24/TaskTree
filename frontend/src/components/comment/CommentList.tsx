import { useState, useEffect, useCallback } from 'react';
import { List, Input, Button, Avatar, message, Empty, Popconfirm } from 'antd';
import { SendOutlined, DeleteOutlined, UserOutlined } from '@ant-design/icons';
import { commentsAPI } from '../../api';
import type { Comment } from '../../types';

const { TextArea } = Input;

interface CommentListProps {
  taskId: number;
}

export default function CommentList({ taskId }: CommentListProps) {
  const [comments, setComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(false);
  const [content, setContent] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const fetchComments = useCallback(async () => {
    setLoading(true);
    try {
      const res = await commentsAPI.list(taskId);
      if (res.code === 200) {
        setComments(Array.isArray(res.data) ? res.data : []);
      }
    } catch (error: any) {
      message.error(error.message || '获取评论失败');
    } finally {
      setLoading(false);
    }
  }, [taskId]);

  useEffect(() => {
    if (taskId) fetchComments();
  }, [taskId, fetchComments]);

  const handleSubmit = async () => {
    if (!content.trim()) {
      message.warning('请输入评论内容');
      return;
    }

    setSubmitting(true);
    try {
      const res = await commentsAPI.create(taskId, { content: content.trim() });
      if (res.code === 201) {
        message.success('评论成功');
        setContent('');
        fetchComments();
      }
    } catch (error: any) {
      message.error(error.message || '评论失败');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (commentId: number) => {
    try {
      const res = await commentsAPI.delete(commentId);
      if (res.code === 200) {
        message.success('删除成功');
        fetchComments();
      }
    } catch (error: any) {
      message.error(error.message || '删除失败');
    }
  };

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <TextArea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="输入评论内容..."
          rows={3}
          style={{ marginBottom: 8 }}
        />
        <Button
          type="primary"
          icon={<SendOutlined />}
          onClick={handleSubmit}
          loading={submitting}
          disabled={!content.trim()}
        >
          发送评论
        </Button>
      </div>

      {comments.length === 0 ? (
        <Empty description="暂无评论" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ) : (
        <List
          loading={loading}
          dataSource={comments}
          renderItem={(item: Comment) => (
            <List.Item
              actions={[
                <Popconfirm
                  title="确定删除？"
                  onConfirm={() => handleDelete(item.id)}
                  okText="删除"
                  cancelText="取消"
                >
                  <Button type="text" size="small" danger icon={<DeleteOutlined />} />
                </Popconfirm>,
              ]}
            >
              <List.Item.Meta
                avatar={<Avatar icon={<UserOutlined />} src={item.user?.avatar} />}
                title={
                  <span>
                    {item.user?.nickname || item.user?.email}
                    <span style={{ fontSize: 12, color: '#999', marginLeft: 8 }}>
                      {new Date(item.created_at).toLocaleString('zh-CN')}
                    </span>
                  </span>
                }
                description={item.content}
              />
            </List.Item>
          )}
        />
      )}
    </div>
  );
}
