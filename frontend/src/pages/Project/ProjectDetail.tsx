import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Button, Input, Modal, Form, Select, DatePicker, Progress, Tag, Space, Dropdown, message, Empty } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, ArrowLeftOutlined, MoreOutlined, ExportOutlined } from '@ant-design/icons';
import { projectsAPI, tasksAPI } from '../../api';
import { STATUS_COLORS, PRIORITY_COLORS, STATUS_LABELS, PRIORITY_LABELS, TASK_STATUS } from '../../constants';

interface Task {
  id: number;
  name: string;
  status: string;
  priority: string;
  progress: number;
  parent_id: number | null;
  children?: Task[];
}

// 任务项组件
function TaskItem({ task, onEdit, onDelete, onAddChild, depth = 0 }: { task: Task; onEdit: (t: Task) => void; onDelete: (t: Task) => void; onAddChild: (t: Task) => void; depth?: number }) {
  const menuItems = [
    { key: 'edit', label: '编辑', icon: <EditOutlined />, onClick: () => onEdit(task) },
    { key: 'add', label: '添加子任务', icon: <PlusOutlined />, onClick: () => onAddChild(task) },
    { key: 'delete', label: '删除', icon: <DeleteOutlined />, danger: true, onClick: () => onDelete(task) },
  ];

  return (
    <div style={{ paddingLeft: depth * 24 }} className="mb-2">
      <Card size="small" className="bg-white">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-gray-400">⋮⋮</span>
            <span className="font-medium">{task.name}</span>
          </div>
          <Space>
            <Tag color={PRIORITY_COLORS[task.priority]}>{PRIORITY_LABELS[task.priority]}</Tag>
            <Tag color={STATUS_COLORS[task.status]}>{STATUS_LABELS[task.status]}</Tag>
            <Progress type="circle" percent={task.progress} width={32} />
            <Dropdown menu={{ items: menuItems }} trigger={['click']}>
              <Button type="text" size="small" icon={<MoreOutlined />} />
            </Dropdown>
          </Space>
        </div>
        {task.children && task.children.length > 0 && (
          <div className="mt-2 border-l-2 border-gray-200 pl-2">
            {task.children.map((child) => (
              <TaskItem key={child.id} task={child} onEdit={onEdit} onDelete={onDelete} onAddChild={onAddChild} depth={depth + 1} />
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

export default function ProjectDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [project, setProject] = useState<any>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(false);
  const [taskModalVisible, setTaskModalVisible] = useState(false);
  const [parentTaskId, setParentTaskId] = useState<number | null>(null);
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [form] = Form.useForm();

  const fetchProject = useCallback(async () => {
    if (!id) return;
    try {
      const res = await projectsAPI.get(Number(id));
      if (res.code === 200) {
        setProject(res.data);
      }
    } catch (error: any) {
      message.error(error.message || '获取项目失败');
    }
  }, [id]);

  const fetchTasks = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const res = await tasksAPI.getTree(Number(id));
      if (res.code === 200) {
        setTasks(res.data || []);
      }
    } catch (error: any) {
      message.error(error.message || '获取任务失败');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    if (id) {
      fetchProject();
      fetchTasks();
    }
  }, [id, fetchProject, fetchTasks]);

  const handleAddTask = (parentTask?: Task) => {
    setParentTaskId(parentTask?.id || null);
    setEditingTask(null);
    form.resetFields();
    setTaskModalVisible(true);
  };

  const handleEditTask = (task: Task) => {
    setEditingTask(task);
    form.setFieldsValue({
      name: task.name,
      status: task.status,
      priority: task.priority,
      progress: task.progress,
    });
    setTaskModalVisible(true);
  };

  const handleDeleteTask = async (task: Task) => {
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除任务"${task.name}"吗？`,
      onOk: async () => {
        try {
          const res = await tasksAPI.delete(task.id);
          if (res.code === 200) {
            message.success('删除成功');
            fetchTasks();
          }
        } catch (error: any) {
          message.error(error.message || '删除失败');
        }
      },
    });
  };

  const handleSubmitTask = async (values: any) => {
    try {
      if (editingTask) {
        await tasksAPI.update(editingTask.id, values);
        message.success('更新成功');
      } else {
        await tasksAPI.create(Number(id), {
          name: values.name,
          description: values.description,
          parent_id: parentTaskId,
          priority: values.priority,
          status: values.status || TASK_STATUS.PENDING,
          progress: values.progress || 0,
          due_date: values.due_date?.format('YYYY-MM-DD'),
        });
        message.success('创建成功');
      }
      setTaskModalVisible(false);
      form.resetFields();
      fetchTasks();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  return (
    <div className="p-6">
      <div className="flex items-center gap-4 mb-6">
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/')}>返回</Button>
        <h1 className="text-2xl font-bold">{project?.name || '项目详情'}</h1>
        <Tag color="blue">{project?.task_count || 0} 个任务</Tag>
        <Tag color="green">{project?.completed_count || 0} 已完成</Tag>
      </div>

      <div className="flex justify-between mb-4">
        <Space>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => handleAddTask()}>
            添加任务
          </Button>
        </Space>
        <Button icon={<ExportOutlined />}>导出</Button>
      </div>

      {tasks.length === 0 ? (
        <Empty description="暂无任务，点击上方按钮添加第一个任务" />
      ) : (
        <div>
          {tasks.map((task) => (
            <TaskItem key={task.id} task={task} onEdit={handleEditTask} onDelete={handleDeleteTask} onAddChild={handleAddTask} />
          ))}
        </div>
      )}

      <Modal
        title={editingTask ? '编辑任务' : '添加任务'}
        open={taskModalVisible}
        onCancel={() => setTaskModalVisible(false)}
        onOk={() => form.submit()}
        width={600}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmitTask}>
          <Form.Item name="name" label="任务名称" rules={[{ required: true, message: '请输入任务名称' }]}>
            <Input placeholder="请输入任务名称" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} placeholder="请输入任务描述" />
          </Form.Item>
          <Space style={{ width: '100%' }}>
            <Form.Item name="priority" label="优先级" initialValue="medium">
              <Select style={{ width: 120 }}>
                {Object.entries(PRIORITY_LABELS).map(([value, label]) => (
                  <Select.Option key={value} value={value}>{label as string}</Select.Option>
                ))}
              </Select>
            </Form.Item>
            <Form.Item name="status" label="状态" initialValue="pending">
              <Select style={{ width: 120 }}>
                {Object.entries(STATUS_LABELS).map(([value, label]) => (
                  <Select.Option key={value} value={value}>{label as string}</Select.Option>
                ))}
              </Select>
            </Form.Item>
            <Form.Item name="progress" label="进度" initialValue={0}>
              <Input type="number" min={0} max={100} style={{ width: 80 }} />
            </Form.Item>
          </Space>
          <Form.Item name="due_date" label="截止日期">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}