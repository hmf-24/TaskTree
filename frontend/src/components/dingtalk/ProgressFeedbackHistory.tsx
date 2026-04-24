/**
 * 进度反馈历史组件
 * 
 * 功能：
 * - 显示进度反馈列表
 * - 支持分页
 * - 支持按任务筛选
 * - 显示解析结果
 */
import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Tag,
  Space,
  Typography,
  Spin,
  message,
  Select,
  Tooltip,
  Empty
} from 'antd';
import {
  ClockCircleOutlined,
  CheckCircleOutlined,
  SyncOutlined,
  WarningOutlined,
  CalendarOutlined,
  QuestionCircleOutlined
} from '@ant-design/icons';
import axios from 'axios';
import type { ColumnsType } from 'antd/es/table';

const { Text, Paragraph } = Typography;
const { Option } = Select;

interface ParsedResult {
  progress_type: string;
  confidence: number;
  keywords: string[];
  progress_value?: number;
  problem_description?: string;
  extend_days?: number;
  raw_message: string;
}

interface ProgressFeedback {
  id: number;
  user_id: number;
  task_id: number;
  message_content: string;
  parsed_result: ParsedResult;
  feedback_type: string;
  created_at: string;
}

interface ProgressFeedbackHistoryProps {
  taskId?: number;
}

const ProgressFeedbackHistory: React.FC<ProgressFeedbackHistoryProps> = ({ taskId }) => {
  const [loading, setLoading] = useState(false);
  const [feedbacks, setFeedbacks] = useState<ProgressFeedback[]>([]);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [selectedTaskId, setSelectedTaskId] = useState<number | undefined>(taskId);

  // 加载反馈历史
  const loadFeedbacks = async (page: number = 1, size: number = 10) => {
    try {
      setLoading(true);
      const params: any = {
        limit: size,
        offset: (page - 1) * size
      };
      
      if (selectedTaskId) {
        params.task_id = selectedTaskId;
      }
      
      const response = await axios.get('/api/v1/dingtalk/progress-feedback', { params });
      
      if (response.data.code === 0) {
        setFeedbacks(response.data.data.items);
        setTotal(response.data.data.total);
      } else {
        message.error('加载失败: ' + response.data.message);
      }
    } catch (error: any) {
      message.error('加载失败: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFeedbacks(currentPage, pageSize);
  }, [currentPage, pageSize, selectedTaskId]);

  // 获取反馈类型图标和颜色
  const getFeedbackTypeTag = (type: string) => {
    const typeMap: Record<string, { icon: React.ReactNode; color: string; text: string }> = {
      completed: { icon: <CheckCircleOutlined />, color: 'success', text: '已完成' },
      in_progress: { icon: <SyncOutlined spin />, color: 'processing', text: '进行中' },
      problem: { icon: <WarningOutlined />, color: 'error', text: '遇到问题' },
      extend: { icon: <CalendarOutlined />, color: 'warning', text: '请求延期' },
      query: { icon: <QuestionCircleOutlined />, color: 'default', text: '查询状态' }
    };
    
    const config = typeMap[type] || { icon: null, color: 'default', text: type };
    
    return (
      <Tag icon={config.icon} color={config.color}>
        {config.text}
      </Tag>
    );
  };

  // 表格列定义
  const columns: ColumnsType<ProgressFeedback> = [
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (text: string) => (
        <Tooltip title={new Date(text).toLocaleString()}>
          <Text type="secondary">
            <ClockCircleOutlined /> {new Date(text).toLocaleString()}
          </Text>
        </Tooltip>
      )
    },
    {
      title: '反馈类型',
      dataIndex: 'feedback_type',
      key: 'feedback_type',
      width: 120,
      render: (type: string) => getFeedbackTypeTag(type)
    },
    {
      title: '消息内容',
      dataIndex: 'message_content',
      key: 'message_content',
      ellipsis: true,
      render: (text: string) => (
        <Paragraph ellipsis={{ rows: 2, expandable: true }} style={{ marginBottom: 0 }}>
          {text}
        </Paragraph>
      )
    },
    {
      title: '解析结果',
      dataIndex: 'parsed_result',
      key: 'parsed_result',
      width: 200,
      render: (result: ParsedResult) => (
        <Space direction="vertical" size="small">
          {result.progress_value !== undefined && (
            <Text>进度: {result.progress_value}%</Text>
          )}
          {result.extend_days !== undefined && result.extend_days > 0 && (
            <Text>延期: {result.extend_days} 天</Text>
          )}
          {result.problem_description && (
            <Tooltip title={result.problem_description}>
              <Text type="danger" ellipsis>问题: {result.problem_description}</Text>
            </Tooltip>
          )}
          {result.keywords && result.keywords.length > 0 && (
            <div>
              {result.keywords.slice(0, 3).map((keyword, index) => (
                <Tag key={index} size="small">{keyword}</Tag>
              ))}
            </div>
          )}
        </Space>
      )
    },
    {
      title: '置信度',
      dataIndex: 'parsed_result',
      key: 'confidence',
      width: 100,
      render: (result: ParsedResult) => {
        const confidence = result.confidence || 0;
        const color = confidence > 0.8 ? 'success' : confidence > 0.5 ? 'warning' : 'error';
        return (
          <Tag color={color}>
            {(confidence * 100).toFixed(0)}%
          </Tag>
        );
      }
    }
  ];

  return (
    <Card
      title="进度反馈历史"
      extra={
        !taskId && (
          <Select
            placeholder="筛选任务"
            style={{ width: 200 }}
            allowClear
            onChange={(value) => {
              setSelectedTaskId(value);
              setCurrentPage(1);
            }}
          >
            {/* 这里可以加载任务列表 */}
            <Option value={undefined}>全部任务</Option>
          </Select>
        )
      }
    >
      <Spin spinning={loading}>
        {feedbacks.length > 0 ? (
          <Table
            columns={columns}
            dataSource={feedbacks}
            rowKey="id"
            pagination={{
              current: currentPage,
              pageSize: pageSize,
              total: total,
              showSizeChanger: true,
              showTotal: (total) => `共 ${total} 条记录`,
              onChange: (page, size) => {
                setCurrentPage(page);
                setPageSize(size);
              }
            }}
          />
        ) : (
          <Empty description="暂无反馈记录" />
        )}
      </Spin>
    </Card>
  );
};

export default ProgressFeedbackHistory;
