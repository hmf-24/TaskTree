import { useState, useEffect } from 'react';
import { List, Button, Space, Typography, message, Popconfirm, Empty, Upload } from 'antd';
import { DownloadOutlined, DeleteOutlined, FileOutlined, UploadOutlined } from '@ant-design/icons';
import type { UploadProps, UploadFile } from 'antd';
import { attachmentsAPI } from '../../api';
import { useAuthStore } from '../../stores/auth';
import type { Attachment } from '../../types';
import { ALLOWED_FILE_EXTENSIONS, MAX_FILE_SIZE } from '../../constants';

const { Text } = Typography;

interface AttachmentListProps {
  taskId: number;
  onUpdate?: () => void;
}

/**
 * 格式化文件大小（字节转 KB/MB）
 * @param bytes 文件大小（字节）
 * @returns 格式化后的文件大小字符串
 */
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
};

/**
 * 格式化日期时间
 * @param dateString ISO 日期字符串
 * @returns 格式化后的日期时间字符串
 */
const formatDateTime = (dateString: string): string => {
  const date = new Date(dateString);
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
};

export default function AttachmentList({ taskId, onUpdate }: AttachmentListProps) {
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [loading, setLoading] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [uploading, setUploading] = useState(false);
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const currentUser = useAuthStore((state) => state.user);

  useEffect(() => {
    fetchAttachments();
  }, [taskId]);

  const fetchAttachments = async () => {
    setLoading(true);
    try {
      const res = await attachmentsAPI.list(taskId);
      console.log('[DEBUG] Attachments API response:', res);
      console.log('[DEBUG] res.code:', res.code);
      console.log('[DEBUG] res.data:', res.data);
      if (res.code === 200) {
        setAttachments(res.data || []);
      }
    } catch (error: any) {
      console.error('[DEBUG] Attachments API error:', error);
      message.error(error.message || '获取附件列表失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (attachment: Attachment) => {
    try {
      await attachmentsAPI.download(attachment.id);
      message.success('下载成功');
    } catch (error: any) {
      message.error(error.message || '下载失败');
    }
  };

  const handleDelete = async (attachmentId: number) => {
    setDeletingId(attachmentId);
    try {
      const res = await attachmentsAPI.delete(attachmentId);
      if (res.code === 200) {
        message.success('删除成功');
        fetchAttachments();
        onUpdate?.();
      }
    } catch (error: any) {
      message.error(error.message || '删除失败');
    } finally {
      setDeletingId(null);
    }
  };

  /**
   * 客户端文件验证（类型和大小）
   * @param file 待上传的文件
   * @returns 是否通过验证
   */
  const beforeUpload = (file: File): boolean | Promise<File> => {
    // 验证文件类型
    const fileExtension = file.name.split('.').pop()?.toLowerCase();
    if (!fileExtension || !ALLOWED_FILE_EXTENSIONS.includes(fileExtension as any)) {
      message.error(`不支持的文件类型: ${fileExtension}`);
      return false;
    }

    // 验证文件大小
    if (file.size > MAX_FILE_SIZE) {
      message.error('文件大小超过限制（最大 50MB）');
      return false;
    }

    return true;
  };

  /**
   * 文件列表变化处理
   * @param info 文件列表信息
   */
  const handleChange: UploadProps['onChange'] = (info) => {
    setFileList(info.fileList);
    
    if (info.file.status === 'uploading') {
      setUploading(true);
    }
    
    if (info.file.status === 'done') {
      setUploading(false);
      message.success('上传成功');
      
      // 清空文件列表
      setFileList([]);
      
      // 刷新附件列表
      fetchAttachments();
      onUpdate?.();
    } else if (info.file.status === 'error') {
      setUploading(false);
      // 尝试从不同的响应格式中提取错误信息
      let errorMsg = '上传失败';
      if (info.file.response) {
        if (typeof info.file.response === 'string') {
          errorMsg = info.file.response;
        } else if (info.file.response.detail) {
          errorMsg = info.file.response.detail;
        } else if (info.file.response.message) {
          errorMsg = info.file.response.message;
        }
      }
      message.error(errorMsg);
      
      // 清空文件列表
      setFileList([]);
    }
  };

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      {/* 上传组件 */}
      <Upload
        fileList={fileList}
        beforeUpload={beforeUpload}
        action={`/api/v1/tasktree/attachments/tasks/${taskId}/attachments`}
        headers={{
          Authorization: `Bearer ${useAuthStore.getState().token}`,
        }}
        onChange={handleChange}
        maxCount={1}
        disabled={uploading}
        onRemove={() => {
          setFileList([]);
          return true;
        }}
      >
        <Button icon={<UploadOutlined />} loading={uploading} disabled={uploading}>
          {uploading ? '上传中...' : '上传附件'}
        </Button>
      </Upload>

      {/* 附件列表 */}
      <List
        loading={loading}
        dataSource={attachments}
        locale={{
          emptyText: (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description="暂无附件"
            />
          ),
        }}
        renderItem={(attachment) => (
          <List.Item
            key={attachment.id}
            actions={[
              <Button
                key="download"
                type="link"
                size="small"
                icon={<DownloadOutlined />}
                onClick={() => handleDownload(attachment)}
              >
                下载
              </Button>,
              <Popconfirm
                key="delete"
                title="确认删除"
                description="确定要删除这个附件吗？"
                onConfirm={() => handleDelete(attachment.id)}
                okText="确定"
                cancelText="取消"
              >
                <Button
                  type="link"
                  size="small"
                  danger
                  icon={<DeleteOutlined />}
                  loading={deletingId === attachment.id}
                >
                  删除
                </Button>
              </Popconfirm>,
            ]}
          >
            <List.Item.Meta
              avatar={<FileOutlined style={{ fontSize: 24, color: '#1890ff' }} />}
              title={
                <Space>
                  <Text strong>{attachment.filename}</Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {formatFileSize(attachment.file_size)}
                  </Text>
                </Space>
              }
              description={
                <Space direction="vertical" size={0}>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    上传时间: {formatDateTime(attachment.created_at)}
                  </Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    上传者: {attachment.user_id === currentUser?.id ? '我' : `用户 ${attachment.user_id}`}
                  </Text>
                </Space>
              }
            />
          </List.Item>
        )}
      />
    </Space>
  );
}
