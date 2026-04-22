import { useMemo, useState } from 'react';
import { Gantt, Task as GanttTask, ViewMode } from 'gantt-task-react';
import 'gantt-task-react/dist/index.css';
import { Empty, Select, Space, Button, Tooltip } from 'antd';
import { PlusOutlined, MinusOutlined, CalendarOutlined } from '@ant-design/icons';
import type { Task } from '../../types';

interface GanttViewProps {
  tasks: Task[];
  onTaskClick?: (task: Task) => void;
  onDateChange?: (task: Task, start: Date, end: Date) => void;
}

export default function GanttView({ tasks, onTaskClick, onDateChange }: GanttViewProps) {
  const [viewMode, setViewMode] = useState<ViewMode>(ViewMode.Day);
  const [columnWidth, setColumnWidth] = useState(50);

  // 扁平化所有任务
  const flatTasks: Task[] = useMemo(() => {
    const result: Task[] = [];
    const flatten = (list: Task[]) => {
      for (const t of list) {
        result.push(t);
        if (t.children) flatten(t.children);
      }
    };
    flatten(tasks);
    return result;
  }, [tasks]);

  const ganttTasks: GanttTask[] = useMemo(() => {
    const now = new Date();
    const oneWeekLater = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);

    return flatTasks
      .filter((t) => t.start_date || t.due_date)
      .map((task) => {
        const start = task.start_date ? new Date(task.start_date) : now;
        const end = task.due_date ? new Date(task.due_date) : oneWeekLater;

        const statusColors: Record<string, string> = {
          pending: '#d9d9d9',
          in_progress: '#1890ff',
          completed: '#52c41a',
          cancelled: '#ff4d4f',
        };

        return {
          id: String(task.id),
          name: task.name,
          start,
          end: end > start ? end : new Date(start.getTime() + 24 * 60 * 60 * 1000),
          progress: task.progress,
          type: 'task' as const,
          styles: {
            progressColor: statusColors[task.status] || '#1890ff',
            progressSelectedColor: statusColors[task.status] || '#1890ff',
            backgroundColor: `${statusColors[task.status] || '#d9d9d9'}40`,
            backgroundSelectedColor: `${statusColors[task.status] || '#d9d9d9'}60`,
          },
          isDisabled: false,
          isMoving: false,
          isSelected: false,
        };
      });
  }, [flatTasks]);

  // 处理任务日期变更（通过拖拽）
  const handleProgressChange = async (task: GanttTask, children: any) => {
    // 找到原始任务
    const originalTask = flatTasks.find((t) => String(t.id) === task.id);
    if (!originalTask || !onDateChange) return;

    try {
      await onDateChange(originalTask, task.start, task.end);
    } catch (error) {
      // 失败不处理
    }
  };

  // 缩放控制
  const handleZoom = (direction: 'in' | 'out') => {
    setColumnWidth((prev) => {
      if (direction === 'in') return Math.min(prev + 20, 150);
      return Math.max(prev - 20, 30);
    });
  };

  const viewModeOptions = [
    { value: ViewMode.Day, label: '日' },
    { value: ViewMode.Week, label: '周' },
    { value: ViewMode.Month, label: '月' },
  ];

  if (ganttTasks.length === 0) {
    return (
      <Empty description="暂无可展示的任务（需要设置开始/截止日期）" style={{ padding: 48 }} />
    );
  }

  return (
    <div>
      <div style={{ marginBottom: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Space>
          <span style={{ fontSize: 13, color: '#666' }}>时间粒度:</span>
          <Select
            value={viewMode}
            onChange={(v) => setViewMode(v)}
            size="small"
            style={{ width: 100 }}
            options={viewModeOptions}
          />
          <Tooltip title="缩小">
            <Button size="small" icon={<MinusOutlined />} onClick={() => handleZoom('out')} />
          </Tooltip>
          <Tooltip title="放大">
            <Button size="small" icon={<PlusOutlined />} onClick={() => handleZoom('in')} />
          </Tooltip>
        </Space>
        <Space>
          <Tooltip title="今天">
            <Button
              size="small"
              icon={<CalendarOutlined />}
              onClick={() => {
                // 滚动到今天位置
                const ganttElement = document.querySelector('.gantt-task-react');
                if (ganttElement) {
                  const todayMarker = document.querySelector('.todayMarker');
                  if (todayMarker) {
                    todayMarker.scrollIntoView({ behavior: 'smooth', inline: 'center' });
                  }
                }
              }}
            />
          </Tooltip>
        </Space>
      </div>
      <div style={{ border: '1px solid #f0f0f0', borderRadius: 8, overflow: 'hidden' }}>
        <Gantt
          tasks={ganttTasks}
          viewMode={viewMode}
          locale="zh"
          listCellWidth=""
          columnWidth={
            viewMode === ViewMode.Month ? 200 :
            viewMode === ViewMode.Week ? 100 :
            columnWidth
          }
          onClick={(task) => {
            const originalTask = flatTasks.find((t) => String(t.id) === task.id);
            if (originalTask && onTaskClick) onTaskClick(originalTask);
          }}
          onDateChange={handleProgressChange}
          onProgressChange={handleProgressChange}
        />
      </div>
    </div>
  );
}
