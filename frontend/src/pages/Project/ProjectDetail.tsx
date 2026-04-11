import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card, Button, Input, Modal, Form, Select, DatePicker, Progress, Tag, Space,
  Dropdown, message, Empty, Segmented, Tooltip, Table
} from 'antd';
import {
  PlusOutlined, EditOutlined, DeleteOutlined, ArrowLeftOutlined,
  MoreOutlined, ExportOutlined, ImportOutlined, HolderOutlined, CheckCircleOutlined,
  PlayCircleOutlined, ClockCircleOutlined, StopOutlined,
  AppstoreOutlined, UnorderedListOutlined, ApartmentOutlined, TagOutlined, BarChartOutlined
} from '@ant-design/icons';
import {
  DndContext, closestCenter, KeyboardSensor, PointerSensor,
  useSensor, useSensors, DragEndEvent, DragStartEvent, DragOverlay
} from '@dnd-kit/core';
import {
  SortableContext, useSortable, verticalListSortingStrategy
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { projectsAPI, tasksAPI } from '../../api';
import { STATUS_COLORS, PRIORITY_COLORS, STATUS_LABELS, PRIORITY_LABELS, TASK_STATUS } from '../../constants';
import TaskDetailDrawer from '../../components/task/TaskDetailDrawer';
import TagManager from '../../components/tag/TagManager';
import ExportModal from '../../components/export/ExportModal';
import ImportModal from '../../components/export/ImportModal';
import GanttView from '../../components/views/GanttView';
import type { Task } from '../../types';

// 状态图标映射
const STATUS_ICONS: Record<string, React.ReactNode> = {
  pending: <ClockCircleOutlined style={{ color: '#8c8c8c' }} />,
  in_progress: <PlayCircleOutlined style={{ color: '#1890ff' }} />,
  completed: <CheckCircleOutlined style={{ color: '#52c41a' }} />,
  cancelled: <StopOutlined style={{ color: '#8c8c8c' }} />,
};

// 状态流转顺序
const STATUS_FLOW: Record<string, string> = {
  pending: 'in_progress',
  in_progress: 'completed',
  completed: 'pending',
  cancelled: 'pending',
};

// 扁平化任务树获取所有任务ID
function flattenTaskIds(tasks: Task[]): string[] {
  const ids: string[] = [];
  const traverse = (list: Task[]) => {
    for (const task of list) {
      ids.push(String(task.id));
      if (task.children && task.children.length > 0) {
        traverse(task.children);
      }
    }
  };
  traverse(tasks);
  return ids;
}

// 在扁平列表中查找任务
function findTaskById(tasks: Task[], id: number): Task | null {
  for (const task of tasks) {
    if (task.id === id) return task;
    if (task.children) {
      const found = findTaskById(task.children, id);
      if (found) return found;
    }
  }
  return null;
}

// 可拖拽的任务项组件
function SortableTaskItem({
  task, onEdit, onDelete, onAddChild, onStatusChange, onOpenDetail, depth = 0
}: {
  task: Task;
  onEdit: (t: Task) => void;
  onDelete: (t: Task) => void;
  onAddChild: (t: Task) => void;
  onStatusChange: (t: Task, newStatus: string) => void;
  onOpenDetail: (t: Task) => void;
  depth?: number;
}) {
  const {
    attributes, listeners, setNodeRef, transform, transition, isDragging
  } = useSortable({ id: String(task.id) });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
    paddingLeft: depth * 24,
  };

  const nextStatus = STATUS_FLOW[task.status];

  const menuItems = [
    { key: 'edit', label: '编辑', icon: <EditOutlined />, onClick: () => onEdit(task) },
    { key: 'add', label: '添加子任务', icon: <PlusOutlined />, onClick: () => onAddChild(task) },
    { type: 'divider' as const },
    { key: 'delete', label: '删除', icon: <DeleteOutlined />, danger: true, onClick: () => onDelete(task) },
  ];

  return (
    <div ref={setNodeRef} style={style} className="mb-2" {...attributes}>
      <Card size="small" className="bg-white" hoverable>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2" style={{ flex: 1, minWidth: 0 }}>
            <span {...listeners} style={{ cursor: 'grab', color: '#bfbfbf', fontSize: 16 }}>
              <HolderOutlined />
            </span>
            <Tooltip title={`点击切换为: ${STATUS_LABELS[nextStatus]}`}>
              <span
                style={{ cursor: 'pointer', fontSize: 16 }}
                onClick={() => onStatusChange(task, nextStatus)}
              >
                {STATUS_ICONS[task.status]}
              </span>
            </Tooltip>
            <span
              className="font-medium"
              style={{
                cursor: 'pointer',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                textDecoration: task.status === 'completed' ? 'line-through' : 'none',
                color: task.status === 'completed' ? '#8c8c8c' : 'inherit',
              }}
              onClick={() => onOpenDetail(task)}
            >
              {task.name}
            </span>
          </div>
          <Space size={4}>
            <Tag color={PRIORITY_COLORS[task.priority]} style={{ margin: 0 }}>{PRIORITY_LABELS[task.priority]}</Tag>
            <Tag color={STATUS_COLORS[task.status]} style={{ margin: 0 }}>{STATUS_LABELS[task.status]}</Tag>
            <Progress type="circle" percent={task.progress} size={28} />
            <Dropdown menu={{ items: menuItems }} trigger={['click']}>
              <Button type="text" size="small" icon={<MoreOutlined />} />
            </Dropdown>
          </Space>
        </div>
        {task.children && task.children.length > 0 && (
          <div className="mt-2 border-l-2 border-gray-200 pl-2">
            <SortableContext items={task.children.map(c => String(c.id))} strategy={verticalListSortingStrategy}>
              {task.children.map((child) => (
                <SortableTaskItem
                  key={child.id}
                  task={child}
                  onEdit={onEdit}
                  onDelete={onDelete}
                  onAddChild={onAddChild}
                  onStatusChange={onStatusChange}
                  onOpenDetail={onOpenDetail}
                  depth={depth + 1}
                />
              ))}
            </SortableContext>
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

  // 详情面板状态
  const [detailTaskId, setDetailTaskId] = useState<number | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);

  // 视图类型
  const [viewType, setViewType] = useState<string>('tree');

  // 标签管理
  const [tagManagerOpen, setTagManagerOpen] = useState(false);

  // 导出/导入
  const [exportOpen, setExportOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);

  // 拖拽活跃项
  const [activeId, setActiveId] = useState<string | null>(null);

  // 拖拽传感器
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor)
  );

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
      content: `确定要删除任务"${task.name}"吗？${task.children && task.children.length > 0 ? '（子任务也会被删除）' : ''}`,
      onOk: async () => {
        try {
          const res = await tasksAPI.delete(task.id, task.children && task.children.length > 0);
          if (res.code === 200) {
            message.success('删除成功');
            fetchTasks();
            fetchProject();
          }
        } catch (error: any) {
          message.error(error.message || '删除失败');
        }
      },
    });
  };

  // 状态快速切换
  const handleStatusChange = async (task: Task, newStatus: string) => {
    try {
      const updateData: any = { status: newStatus };
      // 自动调整进度
      if (newStatus === 'completed') {
        updateData.progress = 100;
      } else if (newStatus === 'pending') {
        updateData.progress = 0;
      } else if (newStatus === 'in_progress' && task.progress === 0) {
        updateData.progress = 10;
      }
      await tasksAPI.update(task.id, updateData);
      message.success(`状态已更新为 ${STATUS_LABELS[newStatus]}`);
      fetchTasks();
    } catch (error: any) {
      message.error(error.message || '状态更新失败');
    }
  };

  // 打开详情面板
  const handleOpenDetail = (task: Task) => {
    setDetailTaskId(task.id);
    setDetailOpen(true);
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
          parent_id: parentTaskId ?? undefined,
          priority: values.priority,
          due_date: values.due_date?.format('YYYY-MM-DD'),
        });
        message.success('创建成功');
      }
      setTaskModalVisible(false);
      form.resetFields();
      fetchTasks();
      fetchProject();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  // 拖拽处理
  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(String(event.active.id));
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveId(null);

    if (!over || active.id === over.id) return;

    const activeTask = findTaskById(tasks, Number(active.id));
    const overTask = findTaskById(tasks, Number(over.id));

    if (!activeTask || !overTask) return;

    try {
      // 移动到目标任务的同级位置
      await tasksAPI.move(activeTask.id, {
        parent_id: overTask.parent_id ?? undefined,
        sort_order: overTask.sort_order,
      });
      fetchTasks();
    } catch (error: any) {
      message.error(error.message || '移动失败');
    }
  };

  const activeTask = activeId ? findTaskById(tasks, Number(activeId)) : null;

  const viewOptions = [
    { value: 'tree', icon: <ApartmentOutlined />, label: '树形' },
    { value: 'kanban', icon: <AppstoreOutlined />, label: '看板' },
    { value: 'list', icon: <UnorderedListOutlined />, label: '列表' },
    { value: 'gantt', icon: <BarChartOutlined />, label: '甘特图' },
  ];

  return (
    <div className="p-6">
      <div className="flex items-center gap-4 mb-6">
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/')}>返回</Button>
        <h1 className="text-2xl font-bold m-0">{project?.name || '项目详情'}</h1>
        <Tag color="blue">{project?.task_count || 0} 个任务</Tag>
        <Tag color="green">{project?.completed_count || 0} 已完成</Tag>
      </div>

      <div className="flex justify-between mb-4">
        <Space>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => handleAddTask()}>
            添加任务
          </Button>
          <Button icon={<TagOutlined />} onClick={() => setTagManagerOpen(true)}>标签管理</Button>
          <Segmented
            options={viewOptions}
            value={viewType}
            onChange={(v) => setViewType(v as string)}
          />
        </Space>
        <Space>
          <Button icon={<ExportOutlined />} onClick={() => setExportOpen(true)}>导出</Button>
          <Button icon={<ImportOutlined />} onClick={() => setImportOpen(true)}>导入</Button>
        </Space>
      </div>

      {/* 树形视图 - 带拖拽 */}
      {viewType === 'tree' && (
        tasks.length === 0 ? (
          <Empty description="暂无任务，点击上方按钮添加第一个任务" />
        ) : (
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
          >
            <SortableContext items={flattenTaskIds(tasks)} strategy={verticalListSortingStrategy}>
              {tasks.map((task) => (
                <SortableTaskItem
                  key={task.id}
                  task={task}
                  onEdit={handleEditTask}
                  onDelete={handleDeleteTask}
                  onAddChild={handleAddTask}
                  onStatusChange={handleStatusChange}
                  onOpenDetail={handleOpenDetail}
                />
              ))}
            </SortableContext>
            <DragOverlay>
              {activeTask ? (
                <Card size="small" className="bg-blue-50 shadow-lg" style={{ opacity: 0.9, width: 'auto' }}>
                  <div className="flex items-center gap-2">
                    <HolderOutlined />
                    <span className="font-medium">{activeTask.name}</span>
                  </div>
                </Card>
              ) : null}
            </DragOverlay>
          </DndContext>
        )
      )}

      {/* 看板视图占位 */}
      {viewType === 'kanban' && (
        <div id="kanban-view-container">
          {/* 将在任务4中实现 */}
          <KanbanView tasks={tasks} onStatusChange={handleStatusChange} onOpenDetail={handleOpenDetail} />
        </div>
      )}

      {/* 列表视图占位 */}
      {viewType === 'list' && (
        <div id="list-view-container">
          <ListView tasks={tasks} onEdit={handleEditTask} onDelete={handleDeleteTask} onStatusChange={handleStatusChange} onOpenDetail={handleOpenDetail} />
        </div>
      )}

      {/* 甘特图视图 */}
      {viewType === 'gantt' && (
        <div id="gantt-view-container">
          <GanttView tasks={tasks} onTaskClick={handleOpenDetail} />
        </div>
      )}

      {/* 添加/编辑任务弹窗 */}
      <Modal
        title={editingTask ? '编辑任务' : (parentTaskId ? '添加子任务' : '添加任务')}
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
            {editingTask && (
              <Form.Item name="status" label="状态" initialValue="pending">
                <Select style={{ width: 120 }}>
                  {Object.entries(STATUS_LABELS).map(([value, label]) => (
                    <Select.Option key={value} value={value}>{label as string}</Select.Option>
                  ))}
                </Select>
              </Form.Item>
            )}
          </Space>
          <Form.Item name="due_date" label="截止日期">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 任务详情面板 */}
      <TaskDetailDrawer
        taskId={detailTaskId}
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
        onUpdate={() => {
          fetchTasks();
          fetchProject();
        }}
      />

      {/* 标签管理 */}
      <TagManager
        projectId={Number(id)}
        open={tagManagerOpen}
        onClose={() => setTagManagerOpen(false)}
      />

      {/* 导出 */}
      <ExportModal
        projectId={Number(id)}
        projectName={project?.name || '项目'}
        open={exportOpen}
        onClose={() => setExportOpen(false)}
      />

      {/* 导入 */}
      <ImportModal
        projectId={Number(id)}
        open={importOpen}
        onClose={() => setImportOpen(false)}
        onSuccess={() => {
          fetchTasks();
          fetchProject();
        }}
      />
    </div>
  );
}

// ========== 看板视图组件 ==========
function KanbanView({
  tasks, onStatusChange, onOpenDetail
}: {
  tasks: Task[];
  onStatusChange: (task: Task, newStatus: string) => void;
  onOpenDetail: (task: Task) => void;
}) {
  // 扁平化所有任务
  const flatTasks: Task[] = [];
  const flatten = (list: Task[]) => {
    for (const t of list) {
      flatTasks.push(t);
      if (t.children) flatten(t.children);
    }
  };
  flatten(tasks);

  const columns = [
    { key: 'pending', title: '待办', color: '#8c8c8c' },
    { key: 'in_progress', title: '进行中', color: '#1890ff' },
    { key: 'completed', title: '已完成', color: '#52c41a' },
    { key: 'cancelled', title: '已取消', color: '#ff4d4f' },
  ];

  return (
    <div style={{ display: 'grid', gridTemplateColumns: `repeat(${columns.length}, 1fr)`, gap: 16 }}>
      {columns.map(col => {
        const colTasks = flatTasks.filter(t => t.status === col.key);
        return (
          <div key={col.key} style={{ background: '#fafafa', borderRadius: 8, padding: 12, minHeight: 300 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12, fontWeight: 600 }}>
              <div style={{ width: 8, height: 8, borderRadius: '50%', background: col.color }} />
              <span>{col.title}</span>
              <Tag style={{ margin: 0 }}>{colTasks.length}</Tag>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {colTasks.map(task => (
                <Card
                  key={task.id}
                  size="small"
                  hoverable
                  onClick={() => onOpenDetail(task)}
                  style={{ cursor: 'pointer' }}
                >
                  <div style={{ marginBottom: 8 }}>
                    <span className="font-medium">{task.name}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Tag color={PRIORITY_COLORS[task.priority]} style={{ margin: 0 }}>
                      {PRIORITY_LABELS[task.priority]}
                    </Tag>
                    <Progress type="circle" percent={task.progress} size={24} />
                  </div>
                  {col.key !== 'completed' && col.key !== 'cancelled' && (
                    <div style={{ marginTop: 8 }}>
                      <Button
                        size="small"
                        type="link"
                        style={{ padding: 0 }}
                        onClick={(e) => {
                          e.stopPropagation();
                          onStatusChange(task, STATUS_FLOW[task.status]);
                        }}
                      >
                        → {STATUS_LABELS[STATUS_FLOW[task.status]]}
                      </Button>
                    </div>
                  )}
                </Card>
              ))}
              {colTasks.length === 0 && (
                <div style={{ textAlign: 'center', color: '#bfbfbf', padding: 24 }}>暂无任务</div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ========== 列表视图组件 ==========
function ListView({
  tasks, onEdit, onDelete, onStatusChange, onOpenDetail
}: {
  tasks: Task[];
  onEdit: (t: Task) => void;
  onDelete: (t: Task) => void;
  onStatusChange: (t: Task, newStatus: string) => void;
  onOpenDetail: (t: Task) => void;
}) {
  // 扁平化所有任务
  const flatTasks: (Task & { depth: number })[] = [];
  const flatten = (list: Task[], depth: number = 0) => {
    for (const t of list) {
      flatTasks.push({ ...t, depth });
      if (t.children) flatten(t.children, depth + 1);
    }
  };
  flatten(tasks);

  const columns = [
    {
      title: '任务名称',
      key: 'name',
      render: (_: any, record: Task & { depth: number }) => (
        <span
          style={{
            paddingLeft: record.depth * 20,
            cursor: 'pointer',
            color: '#1890ff',
            textDecoration: record.status === 'completed' ? 'line-through' : 'none',
          }}
          onClick={() => onOpenDetail(record)}
        >
          {STATUS_ICONS[record.status]} {record.name}
        </span>
      ),
    },
    {
      title: '状态',
      key: 'status',
      width: 100,
      render: (_: any, record: Task) => (
        <Tag
          color={STATUS_COLORS[record.status]}
          style={{ cursor: 'pointer' }}
          onClick={() => onStatusChange(record, STATUS_FLOW[record.status])}
        >
          {STATUS_LABELS[record.status]}
        </Tag>
      ),
    },
    {
      title: '优先级',
      key: 'priority',
      width: 80,
      render: (_: any, record: Task) => (
        <Tag color={PRIORITY_COLORS[record.priority]}>{PRIORITY_LABELS[record.priority]}</Tag>
      ),
    },
    {
      title: '进度',
      key: 'progress',
      width: 80,
      render: (_: any, record: Task) => <Progress percent={record.progress} size="small" />,
    },
    {
      title: '截止日期',
      key: 'due_date',
      width: 120,
      render: (_: any, record: Task) => record.due_date || '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_: any, record: Task) => (
        <Space size={4}>
          <Button type="link" size="small" onClick={() => onEdit(record)}>编辑</Button>
          <Button type="link" size="small" danger onClick={() => onDelete(record)}>删除</Button>
        </Space>
      ),
    },
  ];


  return (
    <Table
      dataSource={flatTasks}
      columns={columns}
      rowKey="id"
      pagination={false}
      size="middle"
    />
  );
}