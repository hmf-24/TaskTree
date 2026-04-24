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

export type TaskStatusType = (typeof TASK_STATUS)[keyof typeof TASK_STATUS];
export type PriorityType = (typeof PRIORITY)[keyof typeof PRIORITY];
export type ProjectStatusType = (typeof PROJECT_STATUS)[keyof typeof PROJECT_STATUS];
export type MemberRoleType = (typeof MEMBER_ROLE)[keyof typeof MEMBER_ROLE];

// 文件附件相关常量
// 允许上传的文件扩展名
export const ALLOWED_FILE_EXTENSIONS = [
  'doc', 'docx', 'pdf', 'txt', 'md',
  'jpg', 'jpeg', 'png', 'gif',
  'zip', 'rar',
  'xls', 'xlsx', 'ppt', 'pptx',
] as const;

// 最大文件大小（50MB）
export const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB in bytes

// 文件类型标签映射（用于显示友好的文件类型名称）
export const FILE_TYPE_LABELS: Record<string, string> = {
  // 文档类型
  doc: 'Word 文档',
  docx: 'Word 文档',
  pdf: 'PDF 文档',
  txt: '文本文件',
  md: 'Markdown 文档',
  // 图片类型
  jpg: 'JPG 图片',
  jpeg: 'JPEG 图片',
  png: 'PNG 图片',
  gif: 'GIF 图片',
  // 压缩包类型
  zip: 'ZIP 压缩包',
  rar: 'RAR 压缩包',
  // 表格和演示文稿类型
  xls: 'Excel 表格',
  xlsx: 'Excel 表格',
  ppt: 'PowerPoint 演示文稿',
  pptx: 'PowerPoint 演示文稿',
};
