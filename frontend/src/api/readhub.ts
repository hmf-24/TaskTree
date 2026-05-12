/**
 * ReadHub API 模块
 * ================
 * 独立的 axios 实例，baseURL 指向 /api/v1/readhub，
 * 复用 TaskTree 的 JWT 拦截器模式。
 */
import axios from 'axios';
import { useAuthStore } from '../stores/auth';

const readhubApi = axios.create({
  baseURL: '/api/v1/readhub',
  timeout: 30000, // RSS 拉取可能较慢
});

// 请求拦截器 — 注入 JWT Token
readhubApi.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().token;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// 响应拦截器 — 解包 data + 401 自动登出
readhubApi.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout();
    }
    return Promise.reject(error.response?.data || error);
  }
);

// ──────────── 订阅源 API ────────────

export const feedsAPI = {
  list: () => readhubApi.get('/feeds'),
  add: (data: { url: string; name: string }) => readhubApi.post('/feeds', data),
  delete: (id: number) => readhubApi.delete(`/feeds/${id}`),
  fetch: () => readhubApi.post('/feeds/fetch'),
};

// ──────────── 文章 API ────────────

export const articlesAPI = {
  list: (params?: {
    feed_id?: number;
    unread_only?: boolean;
    page?: number;
    page_size?: number;
  }) => readhubApi.get('/articles', { params }),
  detail: (id: number) => readhubApi.get(`/articles/${id}`),
  markRead: (id: number) => readhubApi.put(`/articles/${id}/read`),
  saveToObsidian: (id: number) => readhubApi.post(`/articles/${id}/save-to-obsidian`),
  convertToTask: (id: number, data: { project_id: number; title?: string }) =>
    readhubApi.post(`/articles/${id}/convert-to-task`, data),
};

// ──────────── ReadHub 设置 API ────────────

export const readhubSettingsAPI = {
  get: () => readhubApi.get('/settings'),
  update: (data: {
    obsidian_vault_path?: string;
    obsidian_folder?: string;
    auto_fetch_enabled?: boolean;
    auto_fetch_interval?: number;
  }) => readhubApi.put('/settings', data),
  obsidianStatus: () => readhubApi.get('/obsidian/status'),
};

export default readhubApi;
