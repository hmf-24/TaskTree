import { useMemo } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Node,
  Edge,
  Position,
  MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css';
import type { Task, Dependency } from '../../types';

interface DependencyGraphProps {
  tasks: Task[];
  dependencies: Dependency[];
}

export default function DependencyGraph({ tasks, dependencies }: DependencyGraphProps) {
  const { nodes, edges } = useMemo(() => {
    const statusColors: Record<string, string> = {
      pending: '#d9d9d9',
      in_progress: '#1890ff',
      completed: '#52c41a',
      cancelled: '#ff4d4f',
    };

    const taskNodes: Node[] = tasks.map((task, index) => ({
      id: String(task.id),
      position: { x: (index % 4) * 250, y: Math.floor(index / 4) * 120 },
      data: {
        label: (
          <div style={{ padding: 8, textAlign: 'center' }}>
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
      },
      style: {
        border: `2px solid ${statusColors[task.status] || '#d9d9d9'}`,
        borderRadius: 8,
        background: '#fff',
        minWidth: 160,
      },
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
    }));

    const depEdges: Edge[] = dependencies.map((dep) => ({
      id: `dep-${dep.task_id}-${dep.dependent_task_id}`,
      source: String(dep.task_id),
      target: String(dep.dependent_task_id),
      animated: true,
      style: { stroke: '#1890ff' },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#1890ff' },
      label: '依赖',
      labelStyle: { fontSize: 11, fill: '#999' },
    }));

    return { nodes: taskNodes, edges: depEdges };
  }, [tasks, dependencies]);

  if (tasks.length === 0) {
    return <div style={{ textAlign: 'center', padding: 48, color: '#999' }}>暂无任务数据</div>;
  }

  return (
    <div style={{ width: '100%', height: 500, border: '1px solid #f0f0f0', borderRadius: 8 }}>
      <ReactFlow nodes={nodes} edges={edges} fitView attributionPosition="bottom-left">
        <Background />
        <Controls />
        <MiniMap style={{ width: 120, height: 80 }} />
      </ReactFlow>
    </div>
  );
}
