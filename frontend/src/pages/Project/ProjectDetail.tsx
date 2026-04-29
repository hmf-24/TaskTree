import { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card,
  Button,
  Input,
  Modal,
  Form,
  Select,
  DatePicker,
  Progress,
  Tag,
  Space,
  Dropdown,
  message,
  Empty,
  Segmented,
  Tooltip,
  Table,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ArrowLeftOutlined,
  MoreOutlined,
  ExportOutlined,
  ImportOutlined,
  HolderOutlined,
  CheckCircleOutlined,
  PlayCircleOutlined,
  ClockCircleOutlined,
  StopOutlined,
  AppstoreOutlined,
  UnorderedListOutlined,
  ApartmentOutlined,
  TagOutlined,
  BarChartOutlined,
  PlusSquareOutlined,
  MinusSquareOutlined,
  RobotOutlined,
} from '@ant-design/icons';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
  DragStartEvent,
  DragOverlay,
} from '@dnd-kit/core';
import { SortableContext, useSortable, verticalListSortingStrategy, sortableKeyboardCoordinates } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Helmet } from 'react-helmet-async';
import { projectsAPI, tasksAPI } from '../../api';
import {
  STATUS_COLORS,
  PRIORITY_COLORS,
  STATUS_LABELS,
  PRIORITY_LABELS,
  TASK_STATUS,
} from '../../constants';
import AITaskCreatorModal from '../../components/task/AITaskCreatorModal';
import TaskDetailDrawer from '../../components/task/TaskDetailDrawer';
import TagManager from '../../components/tag/TagManager';
import ExportModal from '../../components/export/ExportModal';
import ImportModal from '../../components/export/ImportModal';
import GanttView from '../../components/views/GanttView';
import DependencyGraph from '../../components/dependency/DependencyGraph';
import AIAssistantPanel from '../../components/ai/AIAssistantPanel';
import type { Task, Dependency } from '../../types';

// 状态图标映射（柔和色系）
const STATUS_ICONS: Record<string, React.ReactNode> = {
  pending: <ClockCircleOutlined style={{ color: 'var(--color-ink-tertiary)' }} />,
  in_progress: <PlayCircleOutlined style={{ color: '#1F6C9F' }} />,
  completed: <CheckCircleOutlined style={{ color: '#346538' }} />,
  cancelled: <StopOutlined style={{ color: 'var(--color-ink-tertiary)' }} />,
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

// 扁平化所有任务用于依赖图
function flattenAllTasks(tasks: Task[]): Task[] {
  const result: Task[] = [];
  const traverse = (list: Task[]) => {
    for (const task of list) {
      result.push(task);
      if (task.children && task.children.length > 0) {
        traverse(task.children);
      }
    }
  };
  traverse(tasks);
  return result;
}

// 收集所有任务的依赖关系（从 task.dependencies_from 聚合）
function collectDependencies(tasks: Task[]): Dependency[] {
  const deps: Dependency[] = [];
  const traverse = (list: Task[]) => {
    for (const task of list) {
      if ((task as any).dependencies_from) {
        for (const dep of (task as any).dependencies_from) {
          deps.push(dep);
        }
      }
      if (task.children) traverse(task.children);
    }
  };
  traverse(tasks);
  return deps;
}

// 可拖拽的任务项组件
function SortableTaskItem({
  task,
  onEdit,
  onDelete,
  onAddChild,
  onStatusChange,
  onOpenDetail,
  onSelect,
  selectedId,
  depth = 0,
  expanded = true,
  onToggleExpand,
}: {
  task: Task;
  onEdit: (t: Task) => void;
  onDelete: (t: Task) => void;
  onAddChild: (t: Task) => void;
  onStatusChange: (t: Task, newStatus: string) => void;
  onOpenDetail: (t: Task) => void;
  onSelect?: (t: Task) => void;
  selectedId?: number | null;
  depth?: number;
  expanded?: boolean;
  onToggleExpand?: (t: Task) => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging, data } = useSortable({
    id: String(task.id),
    data: { type: 'task', task },
  });

  const isSelected = selectedId === task.id;

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
    {
      key: 'delete',
      label: '删除',
      icon: <DeleteOutlined />,
      danger: true,
      onClick: () => onDelete(task),
    },
  ];

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
    >
      <div
        className="glass-panel"
        style={{
          background: isSelected ? 'rgba(255,255,255,0.1)' : 'var(--color-surface)',
          border: `1px solid ${isSelected ? 'rgba(255,255,255,0.5)' : 'var(--color-border)'}`,
          borderRadius: 'var(--radius-card)',
          padding: '8px 12px',
          marginBottom: 6,
          cursor: 'pointer',
          transition: 'all var(--duration-fast) var(--ease-smooth)',
          boxShadow: isSelected ? '0 0 0 2px rgba(17,17,17,0.08)' : 'none',
        }}
        onClick={(e) => {
          e.stopPropagation();
          onSelect?.(task);
        }}
        onMouseEnter={(e) => {
          if (!isSelected) {
            (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--color-border-strong)';
            (e.currentTarget as HTMLDivElement).style.boxShadow = 'var(--shadow-card)';
          }
        }}
        onMouseLeave={(e) => {
          if (!isSelected) {
            (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--color-border)';
            (e.currentTarget as HTMLDivElement).style.boxShadow = 'none';
          }
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1, minWidth: 0 }}>
            <span {...listeners} style={{ cursor: 'grab', color: 'var(--color-ink-tertiary)', fontSize: 14 }}>
              <HolderOutlined />
            </span>
            <Tooltip title={`切换为: ${STATUS_LABELS[nextStatus]}`}>
              <span
                style={{ cursor: 'pointer', fontSize: 15, lineHeight: 1 }}
                onClick={(e) => { e.stopPropagation(); onStatusChange(task, nextStatus); }}
              >
                {STATUS_ICONS[task.status]}
              </span>
            </Tooltip>
            <span
              style={{
                cursor: 'pointer',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                textDecoration: task.status === 'completed' ? 'line-through' : 'none',
                color: task.status === 'completed' ? 'var(--color-ink-tertiary)' : 'var(--color-ink)',
                fontSize: 13,
                fontWeight: 500,
              }}
              onClick={(e) => { e.stopPropagation(); onOpenDetail(task); }}
            >
              {task.name}
            </span>
          </div>
          <Space size={4}>
            {task.tags && task.tags.length > 0 && (
              <>
                {task.tags.map((tag) => (
                  <Tag key={tag.id} color={tag.color} style={{ margin: 0, fontSize: 11 }}>
                    {tag.name}
                  </Tag>
                ))}
              </>
            )}
            <Tag color={PRIORITY_COLORS[task.priority]} style={{ margin: 0 }}>
              {PRIORITY_LABELS[task.priority]}
            </Tag>
            <Tag color={STATUS_COLORS[task.status]} style={{ margin: 0 }}>
              {STATUS_LABELS[task.status]}
            </Tag>
            <Progress type="circle" percent={task.progress} size={24} />
            {task.children && task.children.length > 0 && (
              <Button
                type="text"
                size="small"
                icon={expanded ? <MinusSquareOutlined /> : <PlusSquareOutlined />}
                style={{ color: 'var(--color-ink-tertiary)' }}
                onClick={(e) => {
                  e.stopPropagation();
                  onToggleExpand?.(task);
                }}
              />
            )}
            <Tooltip title="添加子任务">
              <Button
                type="text"
                size="small"
                icon={<PlusOutlined />}
                style={{ color: 'var(--color-ink-tertiary)' }}
                onClick={(e) => {
                  e.stopPropagation();
                  onAddChild(task);
                }}
              />
            </Tooltip>
            <Dropdown menu={{ items: menuItems }} trigger={['click']}>
              <Button type="text" size="small" icon={<MoreOutlined />} style={{ color: 'var(--color-ink-tertiary)' }} onClick={(e) => e.stopPropagation()} />
            </Dropdown>
          </Space>
        </div>
        {task.children && task.children.length > 0 && expanded && (
          <div style={{
            marginTop: 6,
            borderLeft: '2px solid var(--color-border)',
            paddingLeft: 8,
            marginLeft: 7,
          }}>
            <SortableContext
              items={task.children.map((c) => String(c.id))}
              strategy={verticalListSortingStrategy}
            >
              {task.children.map((child) => (
                <SortableTaskItem
                  key={child.id}
                  task={child}
                  onEdit={onEdit}
                  onDelete={onDelete}
                  onAddChild={onAddChild}
                  onStatusChange={onStatusChange}
                  onOpenDetail={onOpenDetail}
                  onSelect={onSelect}
                  selectedId={selectedId}
                  depth={depth + 1}
                  expanded={true}
                  onToggleExpand={onToggleExpand}
                />
              ))}
            </SortableContext>
          </div>
        )}
      </div>
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
  const [aiModalVisible, setAiModalVisible] = useState(false);
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

  // AI 助手面板状态
  const [aiPanelOpen, setAiPanelOpen] = useState(false);
  const [aiMode, setAiMode] = useState<'analyze' | 'plan'>('analyze');

  // 选中任务处理
  const handleSelectTask = (task: Task, e?: React.MouseEvent) => {
    if (e?.shiftKey) {
      // Shift+点击：范围选择
      setSelectedTaskId(task.id);
    } else if (e?.ctrlKey || e?.metaKey) {
      // Ctrl+点击：多选切换
      setSelectedIds((prev) => {
        const next = new Set(prev);
        if (next.has(task.id)) {
          next.delete(task.id);
        } else {
          next.add(task.id);
        }
        return next;
      });
      setSelectedTaskId(task.id);
    } else {
      // 普通点击：单选
      setSelectedTaskId(task.id);
      setSelectedIds(new Set());
    }
  };

  // 多选状态
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

  // 展开/收起状态
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set());

  const handleToggleExpand = (task: Task) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(task.id)) {
        next.delete(task.id);
      } else {
        next.add(task.id);
      }
      return next;
    });
  };

  const isExpanded = (taskId: number) => expandedIds.has(taskId);

  // 拖拽活跃项
  const [activeId, setActiveId] = useState<string | null>(null);

  // 选中任务（键盘导航）
  const [selectedTaskId, setSelectedTaskId] = useState<number | null>(null);

  // 拖拽传感器
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
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

  // 键盘快捷键
  useEffect(() => {
    const handleKeyDown = (e: any) => {
      // 忽略输入框中的键盘事件
      if ((e.target as HTMLElement).tagName === 'INPUT' || (e.target as HTMLElement).tagName === 'TEXTAREA') {
        return;
      }

      const key = e.key.toLowerCase();

      // N: 新建任务
      if (key === 'n' && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        handleAddTask();
        return;
      }

      // Delete/Backspace: 删除选中任务
      if ((key === 'delete' || key === 'backspace') && selectedTaskId) {
        e.preventDefault();
        const task = findTaskById(tasks, selectedTaskId);
        if (task) {
          handleDeleteTask(task);
        }
        return;
      }

      // 选中任务时，Enter打开详情
      if (key === 'enter' && selectedTaskId) {
        e.preventDefault();
        const task = findTaskById(tasks, selectedTaskId);
        if (task) {
          handleOpenDetail(task);
        }
        return;
      }

      // Space: 切换选中任务状态
      if (key === ' ' && selectedTaskId) {
        e.preventDefault();
        const task = findTaskById(tasks, selectedTaskId);
        if (task) {
          handleStatusChange(task, STATUS_FLOW[task.status] || 'in_progress');
        }
        return;
      }

      // ArrowUp/ArrowDown: 选中上下任务
      if (key === 'arrowup' || key === 'arrowdown') {
        e.preventDefault();
        const allIds = flattenTaskIds(tasks);
        if (allIds.length === 0) return;
        const currentIdx = selectedTaskId ? allIds.indexOf(String(selectedTaskId)) : -1;
        let newIdx: number;
        if (key === 'arrowup') {
          newIdx = currentIdx <= 0 ? allIds.length - 1 : currentIdx - 1;
        } else {
          newIdx = currentIdx >= allIds.length - 1 ? 0 : currentIdx + 1;
        }
        setSelectedTaskId(Number(allIds[newIdx]));
        return;
      }

      // Escape: 取消选中
      if (key === 'escape') {
        setSelectedTaskId(null);
        return;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [tasks, selectedTaskId]);

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
      description: task.description || '',
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

  // 拖拽处理 - 丝滑版
  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(String(event.active.id));
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over, activatorEvent } = event;
    setActiveId(null);

    if (!over || active.id === over.id) return;

    const activeTaskId = Number(active.id);
    const activeTask = findTaskById(tasks, activeTaskId);
    const overData = over.data.current as { type: string; task?: Task };

    if (!activeTask) return;

    // 判断Ctrl键是否按下（嵌套模式）
    const isCtrlPressed = activatorEvent && (activatorEvent as any).ctrlKey;

    // 获取目标任务
    const overTask = overData?.task;
    if (!overTask) return;

    // 判断拖放模式
    let newParentId: number | undefined;
    let newSortOrder = 0;

    if (isCtrlPressed) {
      // Ctrl+拖拽 → 嵌套为子任务
      newParentId = overTask.id;
      newSortOrder = 0;
    } else {
      // 普通拖拽 → 根据放置位置判断
      // 1. 目标是自己的父任务 → 移到同级顶部
      // 2. 目标是同级任务 → 插入到附近
      // 3. 目标是其他任务 → 判断上下位置
      if (overTask.parent_id === activeTask.parent_id) {
        // 同级任务 - 简单移动到目标位置
        newParentId = overTask.parent_id;
        newSortOrder = overTask.sort_order;
      } else {
        // 不同级 - 变成同级任务
        newParentId = overTask.parent_id;
        newSortOrder = overTask.sort_order;
      }
    }

    // 检查是否形成循环依赖
    if (newParentId) {
      let checkId = newParentId;
      while (checkId) {
        if (checkId === activeTaskId) {
          message.warning('不能将任务移动到其子任务下');
          return;
        }
        const parent = findTaskById(tasks, checkId);
        checkId = parent?.parent_id;
      }
    }

    // 相同位置不需要移动
    if (newParentId === activeTask.parent_id && newSortOrder === activeTask.sort_order) {
      return;
    }

    // 乐观更新 - 立即更新本地状态，不等待API
    setTasks((prev) => {
      const newTasks = JSON.parse(JSON.stringify(prev));

      // 找到并移除任务
      const removeTask = (list: Task[]): Task | null => {
        for (let i = 0; i < list.length; i++) {
          if (list[i].id === activeTaskId) {
            return list.splice(i, 1)[0];
          }
          if (list[i].children?.length) {
            const found = removeTask(list[i].children!);
            if (found) return found;
          }
        }
        return null;
      };

      // 插入任务到新位置
      const insertTask = (list: Task[], parentId: number | undefined, order: number) => {
        // 从列表中获取同级任务
        const siblings = parentId === undefined
          ? list.filter(t => t.parent_id === null || t.parent_id === undefined)
          : list.filter(t => t.parent_id === parentId);

        // 找到要插入的位置
        let insertIndex = siblings.findIndex(t => t.sort_order >= order);
        if (insertIndex === -1) insertIndex = siblings.length;

        // 找到正确的父任务列表
        let targetList = list;
        if (parentId !== undefined) {
          const findParent = (list: Task[]): Task | undefined => {
            for (const t of list) {
              if (t.id === parentId) return t;
              if (t.children?.length) {
                const found = findParent(t.children);
                if (found) return found;
              }
            }
            return undefined;
          };
          const parent = findParent(list);
          targetList = parent?.children || list;
        }

        const task = { ...activeTask, parent_id: parentId, sort_order: order };
        targetList.splice(insertIndex, 0, task);

        // 重新排序
        targetList.forEach((t, i) => { t.sort_order = i; });
      };

      const movedTask = removeTask(newTasks);
      if (movedTask && overTask) {
        movedTask.parent_id = newParentId;
        insertTask(newTasks, newParentId, newSortOrder);
      }

      return newTasks;
    });

    // 调用API
    try {
      await tasksAPI.move(activeTaskId, {
        parent_id: newParentId,
        sort_order: newSortOrder,
      });
    } catch (error: any) {
      // 失败回滚
      message.error(error.message || '移动失败');
      fetchTasks();
    }
  };

  const activeTask = activeId ? findTaskById(tasks, Number(activeId)) : null;

  // 使用 useMemo 缓存视图选项配置
  const viewOptions = useMemo(() => [
    { value: 'tree', icon: <ApartmentOutlined />, label: '树形' },
    { value: 'kanban', icon: <AppstoreOutlined />, label: '看板' },
    { value: 'list', icon: <UnorderedListOutlined />, label: '列表' },
    { value: 'gantt', icon: <BarChartOutlined />, label: '甘特图' },
    { value: 'dependency', icon: <ApartmentOutlined />, label: '依赖图' },
  ], []);

  return (
    <div className="page-container">
      <Helmet><title>{project?.name || '项目详情'} - TaskTree</title></Helmet>

      {/* 页面头部 */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 12,
        marginBottom: 24,
      }}>
        <Button
          type="text"
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate('/')}
          style={{ color: 'var(--color-ink-secondary)' }}
        />
        <div style={{ flex: 1 }}>
          <h1 className="page-title" style={{ marginBottom: 2 }}>{project?.name || '项目详情'}</h1>
          <div style={{ display: 'flex', gap: 12, fontSize: 12, color: 'var(--color-ink-tertiary)' }}>
            <span style={{ fontVariantNumeric: 'tabular-nums' }}>{project?.task_count || 0} 个任务</span>
            <span style={{ fontVariantNumeric: 'tabular-nums' }}>{project?.completed_count || 0} 已完成</span>
          </div>
        </div>

        {/* 项目菜单 */}
        <Dropdown
          menu={{
            items: [
              {
                key: 'rename',
                label: '修改项目名称',
                onClick: () => {
                  const newName = window.prompt('请输入新的项目名称:', project?.name);
                  if (newName && newName.trim()) {
                    projectsAPI.update(Number(id), { name: newName.trim() })
                      .then(() => {
                        message.success('项目名称已更新');
                        fetchProject();
                      })
                      .catch((err) => {
                        message.error(err.message || '更新失败');
                      });
                  }
                }
              },
              {
                key: 'settings',
                label: '项目设置',
                onClick: () => {
                  message.info('项目设置功能开发中...');
                }
              }
            ]
          }}
          trigger={['click']}
        >
          <Button type="text" icon={<MoreOutlined />} style={{ color: 'var(--color-ink-tertiary)' }} />
        </Dropdown>
      </div>

      {/* 工具栏 */}
      <div style={{
        marginBottom: 20,
        paddingBottom: 16,
        borderBottom: '1px solid var(--color-border)',
      }}>
        {/* 移动端：垂直堆叠 */}
        <div className="flex flex-col gap-4 md:hidden">
          <div className="flex flex-col gap-2">
            <span className="section-label">核心操作</span>
            <Space wrap>
              <Button type="primary" icon={<PlusOutlined />} onClick={() => handleAddTask()}>
                添加任务
              </Button>
              <Button 
                onClick={() => setAiModalVisible(true)}
                icon={<RobotOutlined />}
              >
                AI智能创建
              </Button>
              <Button
                icon={<RobotOutlined />}
                onClick={() => {
                  setAiMode('analyze');
                  setAiPanelOpen(true);
                }}
              >
                AI分析
              </Button>
            </Space>
          </div>

          <div className="flex flex-col gap-2">
            <span className="section-label">视图切换</span>
            <Segmented
              options={viewOptions}
              value={viewType}
              onChange={(v) => setViewType(v as string)}
              block
            />
          </div>

          <div className="flex flex-col gap-2">
            <span className="section-label">工具</span>
            <Space wrap>
              <Button icon={<TagOutlined />} onClick={() => setTagManagerOpen(true)}>
                标签管理
              </Button>
              <Button icon={<ExportOutlined />} onClick={() => setExportOpen(true)}>
                导出
              </Button>
              <Button icon={<ImportOutlined />} onClick={() => setImportOpen(true)}>
                导入
              </Button>
            </Space>
          </div>

          {selectedIds.size > 0 && (
            <div className="flex flex-col gap-2">
              <span className="section-label">批量操作</span>
              <Space wrap>
                <Button onClick={() => {
                  Modal.confirm({
                    title: '批量删除',
                    content: `确定要删除选中的 ${selectedIds.size} 个任务吗？`,
                    onOk: async () => {
                      for (const id of selectedIds) {
                        try {
                          await tasksAPI.delete(id, false);
                        } catch (e) {
                          // ignore
                        }
                      }
                      message.success(`已删除 ${selectedIds.size} 个任务`);
                      setSelectedIds(new Set());
                      fetchTasks();
                    }
                  });
                }}>
                  删除选中 ({selectedIds.size})
                </Button>
                <Button onClick={() => {
                  setSelectedIds(new Set());
                  setSelectedTaskId(null);
                }}>
                  取消选择
                </Button>
              </Space>
            </div>
          )}
        </div>

        {/* 桌面端：水平布局 */}
        <div className="hidden md:flex md:justify-between md:items-center">
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <Space>
              <Button type="primary" icon={<PlusOutlined />} onClick={() => handleAddTask()}>
                添加任务
              </Button>
              <Button 
                onClick={() => setAiModalVisible(true)}
                icon={<RobotOutlined />}
              >
                AI智能创建
              </Button>
              <Button
                icon={<RobotOutlined />}
                onClick={() => {
                  setAiMode('analyze');
                  setAiPanelOpen(true);
                }}
              >
                AI分析
              </Button>
              {selectedIds.size > 0 && (
                <>
                  <Button onClick={() => {
                    Modal.confirm({
                      title: '批量删除',
                      content: `确定要删除选中的 ${selectedIds.size} 个任务吗？`,
                      onOk: async () => {
                        for (const id of selectedIds) {
                          try {
                            await tasksAPI.delete(id, false);
                          } catch (e) {
                            // ignore
                          }
                        }
                        message.success(`已删除 ${selectedIds.size} 个任务`);
                        setSelectedIds(new Set());
                        fetchTasks();
                      }
                    });
                  }}>
                    删除选中 ({selectedIds.size})
                  </Button>
                  <Button onClick={() => {
                    setSelectedIds(new Set());
                    setSelectedTaskId(null);
                  }}>
                    取消选择
                  </Button>
                </>
              )}
            </Space>

            <Segmented
              options={viewOptions}
              value={viewType}
              onChange={(v) => setViewType(v as string)}
            />
          </div>

          <Space>
            <Button size="small" icon={<TagOutlined />} onClick={() => setTagManagerOpen(true)}>
              标签
            </Button>
            <Button size="small" icon={<ExportOutlined />} onClick={() => setExportOpen(true)}>
              导出
            </Button>
            <Button size="small" icon={<ImportOutlined />} onClick={() => setImportOpen(true)}>
              导入
            </Button>
          </Space>
        </div>
      </div>

      {/* 树形视图 - 带拖拽 */}
      {viewType === 'tree' &&
        (tasks.length === 0 ? (
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
                  onSelect={handleSelectTask}
                  selectedId={selectedTaskId}
                  expanded={!expandedIds.has(task.id)}
                  onToggleExpand={handleToggleExpand}
                />
              ))}
            </SortableContext>
            <DragOverlay>
              {activeTask ? (
                <div
                  className="glass-panel"
                  style={{
                    padding: '8px 14px',
                    opacity: 0.95,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <HolderOutlined style={{ color: 'var(--color-ink-tertiary)' }} />
                    <span style={{ fontWeight: 500, fontSize: 13 }}>{activeTask.name}</span>
                  </div>
                </div>
              ) : null}
            </DragOverlay>
          </DndContext>
        ))}

      {/* 看板视图占位 */}
      {viewType === 'kanban' && (
        <div id="kanban-view-container">
          {/* 将在任务4中实现 */}
          <KanbanView
            tasks={tasks}
            onStatusChange={handleStatusChange}
            onOpenDetail={handleOpenDetail}
          />
        </div>
      )}

      {/* 列表视图占位 */}
      {viewType === 'list' && (
        <div id="list-view-container">
          <ListView
            tasks={tasks}
            onEdit={handleEditTask}
            onDelete={handleDeleteTask}
            onStatusChange={handleStatusChange}
            onOpenDetail={handleOpenDetail}
          />
        </div>
      )}

      {/* 甘特图视图 */}
      {viewType === 'gantt' && (
        <div id="gantt-view-container">
          <GanttView tasks={tasks} onTaskClick={handleOpenDetail} />
        </div>
      )}

      {/* 依赖关系图视图 (BUG-2-01 fix) */}
      {viewType === 'dependency' && (
        <div id="dependency-view-container">
          <DependencyGraph
            tasks={flattenAllTasks(tasks)}
            dependencies={collectDependencies(tasks)}
          />
        </div>
      )}

      {/* 添加/编辑任务弹窗 */}
      <Modal
        title={editingTask ? '编辑任务' : parentTaskId ? '添加子任务' : '添加任务'}
        open={taskModalVisible}
        onCancel={() => setTaskModalVisible(false)}
        onOk={() => form.submit()}
        width={600}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmitTask}>
          <Form.Item
            name="name"
            label="任务名称"
            rules={[{ required: true, message: '请输入任务名称' }]}
          >
            <Input placeholder="请输入任务名称" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} placeholder="请输入任务描述" />
          </Form.Item>
          <Space style={{ width: '100%' }}>
            <Form.Item name="priority" label="优先级" initialValue="medium">
              <Select style={{ width: 120 }}>
                {Object.entries(PRIORITY_LABELS).map(([value, label]) => (
                  <Select.Option key={value} value={value}>
                    {label as string}
                  </Select.Option>
                ))}
              </Select>
            </Form.Item>
            {editingTask && (
              <Form.Item name="status" label="状态" initialValue="pending">
                <Select style={{ width: 120 }}>
                  {Object.entries(STATUS_LABELS).map(([value, label]) => (
                    <Select.Option key={value} value={value}>
                      {label as string}
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>
            )}
          </Space>
          <Form.Item name="due_date" label="截止日期">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Space style={{ width: '100%' }}>
            <Form.Item name="start_date" label="开始日期">
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="estimated_time" label="预计工时(分钟)">
              <Input type="number" min={0} placeholder="分钟" style={{ width: 120 }} />
            </Form.Item>
          </Space>
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

      {/* AI智能任务创建弹窗 */}
      <AITaskCreatorModal
        projectId={Number(id)}
        parentId={parentTaskId}
        open={aiModalVisible}
        onCancel={() => setAiModalVisible(false)}
        onSuccess={() => {
          setAiModalVisible(false);
          fetchTasks();
          fetchProject();
        }}
      />

      {/* AI 助手面板 */}
      <AIAssistantPanel
        projectId={Number(id)}
        mode={aiMode}
        open={aiPanelOpen}
        onClose={() => setAiPanelOpen(false)}
        onSuccess={() => {
          fetchTasks();
          fetchProject();
        }}
      />
    </div>
  );
}

// ========== 看板视图组件 ==========

// 可拖拽的看板卡片
function DraggableKanbanCard({
  task,
  onStatusChange,
  onOpenDetail,
  colKey,
}: {
  task: Task;
  onStatusChange: (task: Task, newStatus: string) => void;
  onOpenDetail: (task: Task) => void;
  colKey: string;
}) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useSortable({
    id: `kanban-${task.id}`,
    data: { type: 'kanban-card', task, status: task.status },
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    opacity: isDragging ? 0.4 : 1,
    cursor: 'grab',
  };

  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      <Card
        size="small"
        hoverable
        className="glass-panel"
        onClick={() => onOpenDetail(task)}
        style={{ cursor: 'pointer', border: '1px solid rgba(255, 255, 255, 0.1)' }}
      >
        <div style={{ marginBottom: 8 }}>
          <span className="font-medium">{task.name}</span>
        </div>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <Tag color={PRIORITY_COLORS[task.priority]} style={{ margin: 0 }}>
            {PRIORITY_LABELS[task.priority]}
          </Tag>
          <Progress type="circle" percent={task.progress} size={24} />
        </div>
        {colKey !== 'completed' && colKey !== 'cancelled' && (
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
    </div>
  );
}

function KanbanView({
  tasks,
  onStatusChange,
  onOpenDetail,
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
    { key: 'pending', title: '待办', color: '#A3A3A0' },
    { key: 'in_progress', title: '进行中', color: '#1F6C9F' },
    { key: 'completed', title: '已完成', color: '#346538' },
    { key: 'cancelled', title: '已取消', color: '#9F2F2D' },
  ];

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
  );

  // 拖拽处理 - 列之间移动
  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over) return;

    const activeData = active.data.current as { task?: Task };
    const overData = over.data.current as { type?: string; status?: string; task?: Task };
    const draggedTask = activeData?.task;
    if (!draggedTask) return;

    // 判断目标状态：如果拖到列上，取列的 status；如果拖到卡片上，取卡片的 status
    let targetStatus: string | undefined;
    if (overData?.type === 'kanban-column') {
      targetStatus = overData.status;
    } else if (overData?.type === 'kanban-card' && overData.task) {
      targetStatus = overData.task.status;
    }

    if (targetStatus && draggedTask.status !== targetStatus) {
      try {
        await onStatusChange(draggedTask, targetStatus);
      } catch (error) {
        // 失败不处理
      }
    }
  };

  return (
    <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
      <div
        style={{ display: 'grid', gridTemplateColumns: `repeat(${columns.length}, 1fr)`, gap: 16 }}
      >
        {columns.map((col) => {
          const colTasks = flatTasks.filter((t) => t.status === col.key);
          const itemIds = colTasks.map(t => `kanban-${t.id}`);
          return (
            <KanbanColumn key={col.key} colKey={col.key} color={col.color} title={col.title} count={colTasks.length}>
              <SortableContext items={itemIds} strategy={verticalListSortingStrategy}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, minHeight: 60 }}>
                  {colTasks.map((task) => (
                    <DraggableKanbanCard
                      key={task.id}
                      task={task}
                      onStatusChange={onStatusChange}
                      onOpenDetail={onOpenDetail}
                      colKey={col.key}
                    />
                  ))}
                  {colTasks.length === 0 && (
                    <div style={{ textAlign: 'center', color: 'var(--color-ink-tertiary)', padding: 24, fontSize: 13 }}>暂无任务</div>
                  )}
                </div>
              </SortableContext>
            </KanbanColumn>
          );
        })}
      </div>
    </DndContext>
  );
}

// 看板列（droppable）
function KanbanColumn({ colKey, color, title, count, children }: {
  colKey: string; color: string; title: string; count: number; children: React.ReactNode;
}) {
  const { setNodeRef, isOver } = useSortable({
    id: `column-${colKey}`,
    data: { type: 'kanban-column', status: colKey },
  });

  return (
    <div
      ref={setNodeRef}
      className="glass-panel"
      style={{
        background: isOver ? 'rgba(0, 0, 0, 0.3)' : 'rgba(255, 255, 255, 0.03)',
        borderRadius: 'var(--radius-card)',
        padding: 14,
        minHeight: 300,
        transition: 'all var(--duration-normal) var(--ease-smooth)',
        border: isOver ? '2px dashed var(--color-border-strong)' : '2px solid transparent',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          marginBottom: 12,
          fontWeight: 500,
          fontSize: 13,
        }}
      >
        <div style={{ width: 7, height: 7, borderRadius: '50%', background: color }} />
        <span style={{ color: 'var(--color-ink)' }}>{title}</span>
        <span style={{
          fontSize: 11,
          color: 'var(--color-ink-tertiary)',
          fontVariantNumeric: 'tabular-nums',
        }}>{count}</span>
      </div>
      {children}
    </div>
  );
}

// ========== 列表视图组件 ==========
function ListView({
  tasks,
  onEdit,
  onDelete,
  onStatusChange,
  onOpenDetail,
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
            color: 'var(--color-ink)',
            fontWeight: 500,
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
          <Button type="link" size="small" onClick={() => onEdit(record)}>
            编辑
          </Button>
          <Button type="link" size="small" danger onClick={() => onDelete(record)}>
            删除
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <Table dataSource={flatTasks} columns={columns} rowKey="id" pagination={false} size="middle" />
  );
}
