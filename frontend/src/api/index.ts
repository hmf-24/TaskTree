import axios from 'axios';
import { useAuthStore } from '../stores/auth';

const api = axios.create({
  baseURL: '/api/v1/tasktree',
  timeout: 10000,
});

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().token;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// 响应拦截器
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout();
    }
    return Promise.reject(error.response?.data || error);
  }
);

export default api;

// Auth API
export const authAPI = {
  login: (data: { email: string; password: string }) => api.post('/auth/login', data),
  register: (data: { email: string; password: string; nickname: string }) =>
    api.post('/auth/register', data),
  getCurrentUser: () => api.get('/auth/me'),
  updateUser: (data: { nickname?: string; avatar?: string }) => api.put('/auth/me', data),
  changePassword: (data: { old_password: string; new_password: string }) =>
    api.put('/auth/password', data),
};

// Projects API
export const projectsAPI = {
  list: (params?: { status?: string; page?: number; page_size?: number }) =>
    api.get('/projects', { params }),
  get: (id: number) => api.get(`/projects/${id}`),
  create: (data: { name: string; description?: string; start_date?: string; end_date?: string }) =>
    api.post('/projects', data),
  update: (
    id: number,
    data: Partial<{ name: string; description: string; start_date: string; end_date: string }>
  ) => api.put(`/projects/${id}`, data),
  delete: (id: number) => api.delete(`/projects/${id}`),
  archive: (id: number, archived: boolean) => api.post(`/projects/${id}/archive`, { archived }),
  getMembers: (id: number) => api.get(`/projects/${id}/members`),
  addMember: (id: number, data: { email: string; role: string }) =>
    api.post(`/projects/${id}/members`, data),
  removeMember: (id: number, userId: number) => api.delete(`/projects/${id}/members/${userId}`),
};

// Tasks API
export const tasksAPI = {
  getTree: (projectId: number) => api.get(`/projects/${projectId}/tasks/tree`),
  list: (projectId: number, params?: { parent_id?: number; status?: string; priority?: string }) =>
    api.get(`/projects/${projectId}/tasks`, { params }),
  get: (id: number) => api.get(`/tasks/${id}`),
  create: (
    projectId: number,
    data: {
      name: string;
      description?: string;
      parent_id?: number;
      assignee_id?: number;
      priority?: string;
      start_date?: string;
      due_date?: string;
      estimated_time?: number;
    }
  ) => api.post(`/projects/${projectId}/tasks`, data),
  createWithSubtasks: (
    projectId: number,
    data: {
      name: string;
      description?: string;
      priority?: string;
      parent_id?: number | null;
      subtasks: { name: string; description?: string; priority?: string }[];
    }
  ) => api.post(`/projects/${projectId}/tasks/with_subtasks`, data),
  update: (
    id: number,
    data: Partial<{
      name: string;
      description: string;
      assignee_id: number;
      status: string;
      priority: string;
      progress: number;
      start_date: string;
      due_date: string;
      estimated_time: number;
    }>
  ) => api.put(`/tasks/${id}`, data),
  delete: (id: number, deleteChildren?: boolean) =>
    api.delete(`/tasks/${id}`, { params: { delete_children: deleteChildren } }),
  move: (id: number, data: { parent_id?: number; sort_order?: number }) =>
    api.put(`/tasks/${id}/move`, data),
};

// Tags API
export const tagsAPI = {
  list: (projectId: number) => api.get(`/projects/${projectId}/tags`),
  create: (projectId: number, data: { name: string; color?: string }) =>
    api.post(`/projects/${projectId}/tags`, data),
  update: (id: number, data: { name?: string; color?: string }) => api.put(`/tags/${id}`, data),
  delete: (id: number) => api.delete(`/tags/${id}`),
  addToTask: (taskId: number, tagIds: number[]) =>
    api.post(`/tasks/${taskId}/tags`, { tag_ids: tagIds }),
};

// Comments API
export const commentsAPI = {
  list: (taskId: number) => api.get(`/tasks/${taskId}/comments`),
  create: (taskId: number, data: { content: string; mentions?: number[] }) =>
    api.post(`/tasks/${taskId}/comments`, data),
  delete: (id: number) => api.delete(`/comments/${id}`),
};

// Export API
export const exportAPI = {
  json: (projectId: number) =>
    api.get(`/projects/${projectId}/export/json`, { responseType: 'blob' }),
  markdown: (projectId: number) =>
    api.get(`/projects/${projectId}/export/markdown`, { responseType: 'blob' }),
  excel: (projectId: number) =>
    api.get(`/projects/${projectId}/export/excel`, { responseType: 'blob' }),
  importJson: (projectId: number, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post(`/projects/${projectId}/import/json`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};

// Notifications API
export const notificationsAPI = {
  list: (params?: { is_read?: boolean; page?: number; page_size?: number }) =>
    api.get('/notifications', { params }),
  markRead: (id: number) => api.put(`/notifications/${id}/read`),
  markAllRead: () => api.put('/notifications/read-all'),
};

// 智能提醒设置 API
export const reminderSettingsAPI = {
  getSettings: () => api.get('/notifications/settings'),
  updateSettings: (data: {
    dingtalk_webhook?: string;
    dingtalk_secret?: string;
    llm_provider?: string;
    llm_api_key?: string;
    llm_model?: string;
    llm_group_id?: string;
    analysis_config?: object;
    rules?: any[];
    enabled?: boolean;
    daily_limit?: number;
  }) => api.post('/notifications/settings', data),
  getLogs: (params?: { page?: number; page_size?: number }) =>
    api.get('/notifications/logs', { params }),
  getRulesTemplate: () => api.get('/notifications/rules/template'),
  markRead: (logId: number) => api.post(`/notifications/callback/${logId}`),
  // 新增功能
  trigger: () => api.post('/notifications/trigger'),
  getStats: (days?: number) => api.get('/notifications/stats', { params: { days } }),
  testConnection: (data: { provider: string; api_key: string; model: string; group_id?: string }) =>
    api.post('/notifications/test-connection', data, { timeout: 60000 }),
};

// LLM Tasks API
export const llmTasksAPI = {
  clarify: (data: { project_id: number; messages: { role: string; content: string }[] }) =>
    api.post('/llm_tasks/clarify', data, { timeout: 60000 }),
  decompose: (data: { project_id: number; requirement: string }) =>
    api.post('/llm_tasks/decompose', data, { timeout: 60000 }),
};

// Conversations API
export const conversationsAPI = {
  // 创建对话
  create: (data: {
    project_id: number;
    conversation_type: 'create' | 'analyze' | 'modify' | 'plan';
    task_id?: number;
    initial_message?: string;
  }) => api.post('/conversations', data),

  // 发送消息
  sendMessage: (conversationId: number, data: { content: string }) =>
    api.post(`/conversations/${conversationId}/messages`, data, { timeout: 60000 }),

  // 获取对话列表
  list: (params?: { project_id?: number; conversation_type?: string }) =>
    api.get('/conversations', { params }),

  // 获取对话详情
  get: (conversationId: number) => api.get(`/conversations/${conversationId}`),

  // 任务分析
  analyze: (conversationId: number, data?: { focus_areas?: string[] }) =>
    api.post(`/conversations/${conversationId}/analyze`, data, { timeout: 60000 }),

  // 任务修改
  modify: (conversationId: number, data: { modification: any }) =>
    api.post(`/conversations/${conversationId}/modify`, data),

  // 项目规划
  plan: (conversationId: number, data?: { planning_goal?: string }) =>
    api.post(`/conversations/${conversationId}/plan`, data, { timeout: 60000 }),

  // 删除对话
  delete: (conversationId: number) => api.delete(`/conversations/${conversationId}`),
};
