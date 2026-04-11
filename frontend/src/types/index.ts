// ========== 用户类型 ==========
export interface User {
  id: number;
  email: string;
  nickname: string;
  avatar?: string;
}

// ========== 项目类型 ==========
export interface Project {
  id: number;
  name: string;
  description?: string;
  owner_id: number;
  start_date?: string;
  end_date?: string;
  status: string;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
  task_count?: number;
  completed_count?: number;
}

// ========== 任务类型 ==========
export interface Task {
  id: number;
  project_id: number;
  parent_id: number | null;
  name: string;
  description?: string;
  assignee_id?: number | null;
  status: string;
  priority: string;
  progress: number;
  estimated_time?: number | null;
  actual_time?: number | null;
  start_date?: string | null;
  due_date?: string | null;
  sort_order: number;
  created_at?: string;
  updated_at?: string;
  children?: Task[];
  tags?: Tag[];
  dependencies?: Dependency[];
}

// ========== 标签类型 ==========
export interface Tag {
  id: number;
  project_id?: number;
  name: string;
  color?: string;
  created_at?: string;
}

// ========== 依赖关系类型 ==========
export interface Dependency {
  id: number;
  task_id: number;
  dependent_task_id: number;
  created_at?: string;
}

// ========== 评论类型 ==========
export interface Comment {
  id: number;
  task_id: number;
  user_id: number;
  content: string;
  created_at: string;
  user: User;
}

// ========== 通知类型 ==========
export interface Notification {
  id: number;
  user_id: number;
  type: string;
  title?: string;
  content?: string;
  related_id?: number;
  related_type?: string;
  is_read: boolean;
  created_at: string;
}

// ========== API 响应类型 ==========
export interface ApiResponse<T = any> {
  code: number;
  message: string;
  data: T;
}

export interface PaginatedData<T = any> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
