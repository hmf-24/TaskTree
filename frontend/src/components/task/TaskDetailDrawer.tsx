import { useState, useEffect } from 'react';
import {
  Drawer,
  Form,
  Input,
  Select,
  Slider,
  DatePicker,
  Button,
  Tag,
  Space,
  Divider,
  Descriptions,
  message,
} from 'antd';
import { SaveOutlined, CloseOutlined, PlusOutlined, RobotOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { tasksAPI, tagsAPI } from '../../api';
import { STATUS_LABELS, PRIORITY_LABELS, STATUS_COLORS, PRIORITY_COLORS } from '../../constants';
import type { Task, Tag as TagType } from '../../types';
import CommentList from '../comment/CommentList';
import AIAssistantPanel from '../ai/AIAssistantPanel';
import AttachmentList from './AttachmentList';

interface TaskDetailDrawerProps {
  taskId: number | null;
  open: boolean;
  onClose: () => void;
  onUpdate: () => void;
}

export default function TaskDetailDrawer({
  taskId,
  open,
  onClose,
  onUpdate,
}: TaskDetailDrawerProps) {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [taskDetail, setTaskDetail] = useState<any>(null);
  const [projectTags, setProjectTags] = useState<TagType[]>([]);
  const [selectedTagIds, setSelectedTagIds] = useState<number[]>([]);
  const [savingTags, setSavingTags] = useState(false);

  // AI 助手面板状态
  const [aiPanelOpen, setAiPanelOpen] = useState(false);

  useEffect(() => {
    if (taskId && open) {
      fetchTaskDetail();
    }
  }, [taskId, open]);

  const fetchTaskDetail = async () => {
    if (!taskId) return;
    setLoading(true);
    try {
      const res = await tasksAPI.get(taskId);
      if (res.code === 200) {
        setTaskDetail(res.data);
        form.setFieldsValue({
          name: res.data.name,
          description: res.data.description || '',
          status: res.data.status,
          priority: res.data.priority,
          progress: res.data.progress,
          estimated_time: res.data.estimated_time,
          actual_time: res.data.actual_time,
          start_date: res.data.start_date ? dayjs(res.data.start_date) : null,
          due_date: res.data.due_date ? dayjs(res.data.due_date) : null,
        });

        // 加载项目标签
        if (res.data.project_id) {
          try {
            const tagRes = await tagsAPI.list(res.data.project_id);
            if (tagRes.code === 200) {
              setProjectTags(Array.isArray(tagRes.data) ? tagRes.data : []);
            }
          } catch { /* ignore */ }
        }

        // 设置已选标签
        const existingTags = res.data.tags || [];
        setSelectedTagIds(existingTags.map((t: TagType) => t.id));
      }
    } catch (error: any) {
      message.error(error.message || '获取任务详情失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!taskId) return;
    try {
      const values = await form.validateFields();
      setSaving(true);

      const updateData: any = {
        name: values.name,
        description: values.description,
        status: values.status,
        priority: values.priority,
        progress: values.progress,
        estimated_time: values.estimated_time || null,
        actual_time: values.actual_time || null,
        start_date: values.start_date?.format('YYYY-MM-DD') || null,
        due_date: values.due_date?.format('YYYY-MM-DD') || null,
      };

      const res = await tasksAPI.update(taskId, updateData);
      if (res.code === 200) {
        message.success('保存成功');
        onUpdate();
      }
    } catch (error: any) {
      if (error.errorFields) return; // form validation error
      message.error(error.message || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  const handleSaveTags = async () => {
    if (!taskId) return;
    setSavingTags(true);
    try {
      const res = await tagsAPI.addToTask(taskId, selectedTagIds);
      if (res.code === 200) {
        message.success('标签已更新');
        fetchTaskDetail();
      }
    } catch (error: any) {
      message.error(error.message || '标签更新失败');
    } finally {
      setSavingTags(false);
    }
  };

  const handleStatusChange = (newStatus: string) => {
    form.setFieldValue('status', newStatus);
    // 自动调整进度
    if (newStatus === 'completed') {
      form.setFieldValue('progress', 100);
    } else if (newStatus === 'pending') {
      form.setFieldValue('progress', 0);
    }
  };

  return (
    <Drawer
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span>任务详情</span>
          {taskDetail && (
            <>
              <Tag color={STATUS_COLORS[taskDetail.status]}>{STATUS_LABELS[taskDetail.status]}</Tag>
              <Tag color={PRIORITY_COLORS[taskDetail.priority]}>
                {PRIORITY_LABELS[taskDetail.priority]}
              </Tag>
            </>
          )}
        </div>
      }
      placement="right"
      width={520}
      open={open}
      onClose={onClose}
      loading={loading}
      extra={
        <Space>
          <Button onClick={onClose} icon={<CloseOutlined />}>
            取消
          </Button>
          <Button
            icon={<RobotOutlined />}
            onClick={() => setAiPanelOpen(true)}
            style={{ color: '#52c41a', borderColor: '#52c41a' }}
          >
            AI 修改
          </Button>
          <Button type="primary" onClick={handleSave} loading={saving} icon={<SaveOutlined />}>
            保存
          </Button>
        </Space>
      }
    >
      <Form form={form} layout="vertical" size="middle">
        <Form.Item
          name="name"
          label="任务名称"
          rules={[{ required: true, message: '请输入任务名称' }]}
        >
          <Input placeholder="请输入任务名称" />
        </Form.Item>

        <Form.Item name="description" label="任务描述">
          <Input.TextArea rows={4} placeholder="请输入任务描述..." />
        </Form.Item>

        <Divider />

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <Form.Item name="status" label="状态">
            <Select onChange={handleStatusChange}>
              {Object.entries(STATUS_LABELS).map(([value, label]) => (
                <Select.Option key={value} value={value}>
                  {label as string}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="priority" label="优先级">
            <Select>
              {Object.entries(PRIORITY_LABELS).map(([value, label]) => (
                <Select.Option key={value} value={value}>
                  {label as string}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
        </div>

        <Form.Item name="progress" label="进度">
          <Slider marks={{ 0: '0%', 25: '25%', 50: '50%', 75: '75%', 100: '100%' }} step={5} />
        </Form.Item>

        <Divider />

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <Form.Item name="start_date" label="开始日期">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="due_date" label="截止日期">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <Form.Item name="estimated_time" label="预计工时(分钟)">
            <Input type="number" min={0} placeholder="分钟" />
          </Form.Item>
          <Form.Item name="actual_time" label="实际工时(分钟)">
            <Input type="number" min={0} placeholder="分钟" />
          </Form.Item>
        </div>

        {/* 标签编辑 */}
        <Divider />
        <div>
          <span style={{ fontWeight: 500, marginBottom: 8, display: 'block' }}>标签</span>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Select
              mode="multiple"
              placeholder="选择标签"
              value={selectedTagIds}
              onChange={setSelectedTagIds}
              style={{ width: '100%' }}
              optionLabelProp="label"
            >
              {projectTags.map((tag) => (
                <Select.Option key={tag.id} value={tag.id} label={tag.name}>
                  <Tag color={tag.color} style={{ margin: 0 }}>{tag.name}</Tag>
                </Select.Option>
              ))}
            </Select>
            <Button
              size="small"
              type="primary"
              ghost
              onClick={handleSaveTags}
              loading={savingTags}
              icon={<PlusOutlined />}
            >
              保存标签
            </Button>
          </Space>
        </div>

        {taskDetail?.children && taskDetail.children.length > 0 && (
          <>
            <Divider />
            <Descriptions title="子任务" column={1} size="small">
              {taskDetail.children.map((child: any) => (
                <Descriptions.Item
                  key={child.id}
                  label={
                    <Tag color={STATUS_COLORS[child.status]} style={{ margin: 0 }}>
                      {STATUS_LABELS[child.status]}
                    </Tag>
                  }
                >
                  {child.name}
                </Descriptions.Item>
              ))}
            </Descriptions>
          </>
        )}
      </Form>

      {/* 评论区 */}
      {taskId && taskDetail && (
        <>
          <Divider />
          <div style={{ fontWeight: 600, marginBottom: 12 }}>评论</div>
          <CommentList taskId={taskId} />
        </>
      )}

      {/* 附件区 */}
      {taskId && taskDetail && (
        <>
          <Divider />
          <div style={{ fontWeight: 600, marginBottom: 12 }}>附件</div>
          <AttachmentList taskId={taskId} onUpdate={fetchTaskDetail} />
        </>
      )}

      {/* AI 助手面板 */}
      {taskId && taskDetail && (
        <AIAssistantPanel
          projectId={taskDetail.project_id}
          mode="modify"
          taskId={taskId}
          open={aiPanelOpen}
          onClose={() => setAiPanelOpen(false)}
          onSuccess={() => {
            fetchTaskDetail();
            onUpdate();
          }}
        />
      )}
    </Drawer>
  );
}
