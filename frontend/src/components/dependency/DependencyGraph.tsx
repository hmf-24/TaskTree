import { useMemo, useCallback } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Node,
  Edge,
  Position,
  MarkerType,
  useNodesState,
  useEdgesState,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Select, Space, Tooltip, Button } from 'antd';
import { FullscreenOutlined, AimOutlined } from '@ant-design/icons';
import type { Task, Dependency } from '../../types';
import { useState } from 'react';

interface DependencyGraphProps {
  tasks: Task[];
  dependencies: Dependency[];
  onTaskClick?: (task: Task) => void;
}

export default function DependencyGraph({ tasks, dependencies, onTaskClick }: DependencyGraphProps) {
  const [showLabels, setShowLabels] = useState(true);
  const [layoutType, setLayoutType] = useState<'grid' | 'dagre'>('grid');

  // 节点和边的数据结构
  const { nodes: initNodes, edges: initEdges } = useMemo(() => {
    const statusColors: Record<string, string> = {
      pending: '#d9d9d9',
      in_progress: '#1890ff',
      completed: '#52c41a',
      cancelled: '#ff4d4f',
    };

    // 使用Dagre进行自动布局
    const computeLayout = () => {
      const nodeMap = new Map<number, { x: number; y: number; width: number; height: number }>();
      const levels = new Map<number, number>();
      const queue: number[] = [];
      const visited = new Set<number>();

      // 找到根节点（没有被依赖的任务）
      const dependentIds = new Set(dependencies.map(d => d.dependent_task_id));
      const rootTasks = tasks.filter(t => !dependentIds.has(t.id));
      rootTasks.forEach(t => {
        levels.set(t.id, 0);
        queue.push(t.id);
      });

      // BFS计算层级
      while (queue.length > 0) {
        const taskId = queue.shift()!;
        if (visited.has(taskId)) continue;
        visited.add(taskId);

        const level = levels.get(taskId) || 0;

        // 找到依赖此任务的任务
        const dependents = dependencies.filter(d => d.task_id === taskId);
        for (const dep of dependents) {
          if (!levels.has(dep.dependent_task_id) || levels.get(dep.dependent_task_id)! < level + 1) {
            levels.set(dep.dependent_task_id, level + 1);
            queue.push(dep.dependent_task_id);
          }
        }
      }

      // 未被任何任务依赖的设为0级
      tasks.forEach(t => {
        if (!levels.has(t.id)) levels.set(t.id, 0);
      });

      // 按层级和位置排序
      const levelGroups = new Map<number, Task[]>();
      tasks.forEach(t => {
        const level = levels.get(t.id) || 0;
        if (!levelGroups.has(level)) levelGroups.set(level, []);
        levelGroups.get(level)!.push(t);
      });

      // 布局计算
      const maxLevel = Math.max(...Array.from(levels.values()), 0);
      const tasksPerLevel = Math.ceil(tasks.length / (maxLevel + 1));

      taskMap.clear();
      let index = 0;
      for (const [level, levelTasks] of levelGroups) {
        levelTasks.forEach((task, i) => {
          taskMap.set(task.id, {
            x: level * 280,
            y: (i % tasksPerLevel) * 100,
            width: 180,
            height: 60,
          });
          index++;
        });
      }

      return taskMap;
    };

    const layout = layoutType === 'dagre' ? computeLayout() : null;

    // 构建节点
    const taskNodes: Node[] = tasks.map((task, index) => {
      const pos = layout?.get(task.id) || { x: (index % 4) * 250, y: Math.floor(index / 4) * 120 };

      return {
        id: String(task.id),
        position: { x: pos.x, y: pos.y },
        data: {
          label: (
            <div style={{ padding: 8, textAlign: 'center', cursor: 'pointer' }}>
              <div style={{ fontWeight: 600, fontSize: 13 }}>{task.name}</div>
              <div
                style={{
                  fontSize: 11,
                  color: statusColors[task.status],
                  marginTop: 4,
                  display: 'inline-block',
                  padding: '1px 6px',
                  borderRadius: 4,
                  background: `${statusColors[task.status]}20`,
                }}
              >
                {task.status === 'pending'
                  ? '待办'
                  : task.status === 'in_progress'
                    ? '进行中'
                    : task.status === 'completed'
                      ? '已完成'
                      : '已取消'}
              </div>
            </div>
          ),
          task,
        },
        style: {
          border: `2px solid ${statusColors[task.status] || '#d9d9d9'}`,
          borderRadius: 8,
          background: '#fff',
          minWidth: 160,
        },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
      };
    });

    // 构建边
    const depEdges: Edge[] = dependencies.map((dep) => ({
      id: `dep-${dep.task_id}-${dep.dependent_task_id}`,
      source: String(dep.task_id),
      target: String(dep.dependent_task_id),
      animated: true,
      style: { stroke: '#1890ff' },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#1890ff' },
      label: showLabels ? '依赖' : undefined,
      labelStyle: { fontSize: 11, fill: '#999' },
    }));

    return { nodes: taskNodes, edges: depEdges };
  }, [tasks, dependencies, showLabels, layoutType]);

  // 处理节点点击
  const handleNodeClick = useCallback((_: any, node: Node) => {
    if (onTaskClick && node.data?.task) {
      onTaskClick(node.data.task);
    }
  }, [onTaskClick]);

  if (tasks.length === 0) {
    return <div style={{ textAlign: 'center', padding: 48, color: '#999' }}>暂无任务数据</div>;
  }

  return (
    <div>
      <div style={{ marginBottom: 12 }}>
        <Space>
          <span style={{ fontSize: 13, color: '#666' }}>布局:</span>
          <Select
            value={layoutType}
            onChange={(v) => setLayoutType(v)}
            size="small"
            style={{ width: 80 }}
            options={[
              { value: 'grid', label: '网格' },
              { value: 'dagre', label: '自动' },
            ]}
          />
          <Select
            value={showLabels}
            onChange={(v) => setShowLabels(v)}
            size="small"
            style={{ width: 80 }}
            options={[
              { value: true, label: '显示' },
              { value: false, label: '隐藏' },
            ]}
          />
        </Space>
      </div>
      <div style={{ width: '100%', height: 500, border: '1px solid #f0f0f0', borderRadius: 8 }}>
        <ReactFlow
          nodes={initNodes}
          edges={initEdges}
          fitView
          attributionPosition="bottom-left"
          onNodeClick={handleNodeClick}
        >
          <Background />
          <Controls />
          <MiniMap style={{ width: 120, height: 80 }} />
        </ReactFlow>
      </div>
    </div>
  );
}
