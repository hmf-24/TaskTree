import { useMemo } from 'react';
import { Gantt, Task as GanttTask, ViewMode } from 'gantt-task-react';
import 'gantt-task-react/dist/index.css';
import { Empty, Select, Space } from 'antd';
import { useState } from 'react';
import type { Task } from '../../types';

interface GanttViewProps {
  tasks: Task[];
  onTaskClick?: (task: Task) => void;
}

export default function GanttView({ tasks, onTaskClick }: GanttViewProps) {
  const [viewMode, setViewMode] = useState<ViewMode>(ViewMode.Day);

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
      .filter(t => t.start_date || t.due_date) // 只显示有日期的任务
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
        };
      });
  }, [flatTasks]);

  if (ganttTasks.length === 0) {
    return (
      <Empty
        description="暂无可展示的任务（需要设置开始/截止日期）"
        style={{ padding: 48 }}
      />
    );
  }

  return (
    <div>
      <div style={{ marginBottom: 12 }}>
        <Space>
          <span style={{ fontSize: 13, color: '#666' }}>时间粒度:</span>
          <Select
            value={viewMode}
            onChange={(v) => setViewMode(v)}
            size="small"
            style={{ width: 100 }}
            options={[
              { value: ViewMode.Day, label: '日' },
              { value: ViewMode.Week, label: '周' },
              { value: ViewMode.Month, label: '月' },
            ]}
          />
        </Space>
      </div>
      <div style={{ border: '1px solid #f0f0f0', borderRadius: 8, overflow: 'hidden' }}>
        <Gantt
          tasks={ganttTasks}
          viewMode={viewMode}
          locale="zh"
          listCellWidth=""
          columnWidth={viewMode === ViewMode.Month ? 200 : viewMode === ViewMode.Week ? 100 : 50}
          onClick={(task) => {
            const originalTask = flatTasks.find(t => String(t.id) === task.id);
            if (originalTask && onTaskClick) onTaskClick(originalTask);
          }}
        />
      </div>
    </div>
  );
}
