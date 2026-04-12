// 任务状态
export const TASK_STATUS = {
  PENDING: 'pending',
  IN_PROGRESS: 'in_progress',
  COMPLETED: 'completed',
  CANCELLED: 'cancelled',
} as const;

// 任务优先级
export const PRIORITY = {
  HIGH: 'high',
  MEDIUM: 'medium',
  LOW: 'low',
} as const;

// 项目状态
export const PROJECT_STATUS = {
  ACTIVE: 'active',
  ARCHIVED: 'archived',
} as const;

// 成员角色（与后端 constants.py MemberRole 保持一致）
export const MEMBER_ROLE = {
  OWNER: 'owner',
  ADMIN: 'admin',
  MEMBER: 'member',
  VIEWER: 'viewer',
} as const;

// 状态颜色映射
export const STATUS_COLORS: Record<string, string> = {
  pending: 'default',
  in_progress: 'processing',
  completed: 'success',
  cancelled: 'default',
};

// 优先级颜色映射
export const PRIORITY_COLORS: Record<string, string> = {
  high: 'red',
  medium: 'orange',
  low: 'green',
};

// 状态标签映射
export const STATUS_LABELS: Record<string, string> = {
  pending: '待办',
  in_progress: '进行中',
  completed: '已完成',
  cancelled: '已取消',
};

// 优先级标签映射
export const PRIORITY_LABELS: Record<string, string> = {
  high: '高',
  medium: '中',
  low: '低',
};

export type TaskStatusType = typeof TASK_STATUS[keyof typeof TASK_STATUS];
export type PriorityType = typeof PRIORITY[keyof typeof PRIORITY];
export type ProjectStatusType = typeof PROJECT_STATUS[keyof typeof PROJECT_STATUS];
export type MemberRoleType = typeof MEMBER_ROLE[keyof typeof MEMBER_ROLE];