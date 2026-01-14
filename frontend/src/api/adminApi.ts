import axios from 'axios';
import { useAuthStore } from '../stores/authStore';
import { API_BASE_URL } from '../config/api';
import type {
  CurrentUser,
  AdminUser,
  UserListResponse,
  LoginResponse,
  CreateUserRequest,
  AssignRoleRequest,
} from '../types/user';

// Re-export types for backwards compatibility
export type { CurrentUser as UserInfo, AdminUser as User, UserListResponse, LoginResponse, CreateUserRequest };

// Create axios instance with auth interceptor
export const adminApi = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
adminApi.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 responses
adminApi.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout();
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// =============================================================================
// Auth API
// =============================================================================

export interface LoginRequest {
  username: string;
  password: string;
}

export interface DevUser {
  email: string;
  role: string;
  is_superuser: boolean;
  full_name: string | null;
}

export interface DevUsersResponse {
  users: DevUser[];
  enabled: boolean;
}

export const authApi = {
  login: async (data: LoginRequest): Promise<LoginResponse> => {
    const formData = new FormData();
    formData.append('username', data.username);
    formData.append('password', data.password);

    const response = await adminApi.post('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    return response.data;
  },

  getMe: async (): Promise<CurrentUser> => {
    const response = await adminApi.get('/auth/me');
    return response.data;
  },

  // Dev tools (only in dev mode)
  devGetUsers: async (): Promise<DevUsersResponse> => {
    const response = await adminApi.get('/auth/dev/users');
    return response.data;
  },

  devLogin: async (role: string): Promise<LoginResponse> => {
    const response = await adminApi.post('/auth/dev/login', { role });
    return response.data;
  },
};

// =============================================================================
// Users API
// =============================================================================

export const usersApi = {
  list: async (params?: { skip?: number; limit?: number; role?: string; domain?: string }): Promise<UserListResponse> => {
    const response = await adminApi.get('/api/admin/users', { params });
    return response.data;
  },

  get: async (id: number): Promise<AdminUser> => {
    const response = await adminApi.get(`/api/admin/users/${id}`);
    return response.data;
  },

  create: async (data: CreateUserRequest): Promise<AdminUser> => {
    const response = await adminApi.post('/api/admin/users', data);
    return response.data;
  },

  update: async (id: number, data: Partial<AdminUser>): Promise<AdminUser> => {
    const response = await adminApi.patch(`/api/admin/users/${id}`, data);
    return response.data;
  },

  delete: async (id: number): Promise<void> => {
    await adminApi.delete(`/api/admin/users/${id}`);
  },

  assignRole: async (data: AssignRoleRequest): Promise<AdminUser> => {
    const response = await adminApi.post('/api/admin/users/assign-role', data);
    return response.data.user;
  },
};

// =============================================================================
// Stats API
// =============================================================================

export interface GlobalStats {
  users: {
    total_users: number;
    active_users: number;
    superusers: number;
    by_role: Record<string, number>;
    by_domain: Record<string, number>;
  };
  transcriptions: {
    pending: number;
    processing: number;
    completed: number;
    failed: number;
    total: number;
  };
  storage: {
    total_bytes: number;
    total_mb: number;
    total_gb: number;
    uploads_bytes: number;
    outputs_bytes: number;
  };
  domains: {
    construction: number;
    hr: number;
    general: number;
  };
  redis_connected: boolean;
  gpu_available: boolean;
  generated_at: string;
}

export interface SystemHealth {
  status: string;
  redis: boolean;
  database: boolean;
  gpu: boolean;
  celery: boolean;
  disk_usage_percent: number;
  memory_usage_percent: number;
}

export const statsApi = {
  getGlobal: async (): Promise<GlobalStats> => {
    const response = await adminApi.get('/api/admin/stats/global');
    return response.data;
  },

  getHealth: async (): Promise<SystemHealth> => {
    const response = await adminApi.get('/api/admin/stats/health');
    return response.data;
  },
};

// =============================================================================
// Settings API
// =============================================================================

export interface SystemSetting {
  key: string;
  value: string;
  description: string | null;
  updated_at: string;
  updated_by: string | null;
}

export interface SettingsListResponse {
  settings: SystemSetting[];
  total: number;
}

export const settingsApi = {
  list: async (): Promise<SettingsListResponse> => {
    const response = await adminApi.get('/api/admin/settings');
    return response.data;
  },

  get: async (key: string): Promise<SystemSetting> => {
    const response = await adminApi.get(`/api/admin/settings/${key}`);
    return response.data;
  },

  update: async (key: string, value: string, description?: string): Promise<SystemSetting> => {
    const response = await adminApi.put(`/api/admin/settings/${key}`, { value, description });
    return response.data;
  },

  create: async (key: string, value: string, description?: string): Promise<SystemSetting> => {
    const response = await adminApi.post('/api/admin/settings', { key, value, description });
    return response.data;
  },

  delete: async (key: string): Promise<void> => {
    await adminApi.delete(`/api/admin/settings/${key}`);
  },

  initialize: async (): Promise<{ created: number }> => {
    const response = await adminApi.post('/api/admin/settings/initialize');
    return response.data;
  },
};

// =============================================================================
// Error Logs API
// =============================================================================

export interface ErrorLog {
  id: number;
  timestamp: string;
  endpoint: string;
  method: string;
  error_type: string;
  error_detail: string;
  user_id: number | null;
  user_email: string | null;
  request_body: string | null;
  status_code: number;
}

export interface ErrorLogListResponse {
  logs: ErrorLog[];
  total: number;
  page: number;
  page_size: number;
}

export interface ErrorLogSummary {
  total_errors: number;
  errors_today: number;
  errors_this_week: number;
  by_endpoint: Record<string, number>;
  by_error_type: Record<string, number>;
  by_status_code: Record<number, number>;
}

export const logsApi = {
  list: async (params?: { page?: number; page_size?: number; endpoint?: string; error_type?: string }): Promise<ErrorLogListResponse> => {
    const response = await adminApi.get('/api/admin/logs', { params });
    return response.data;
  },

  get: async (id: number): Promise<ErrorLog> => {
    const response = await adminApi.get(`/api/admin/logs/${id}`);
    return response.data;
  },

  getSummary: async (): Promise<ErrorLogSummary> => {
    const response = await adminApi.get('/api/admin/logs/summary');
    return response.data;
  },

  cleanup: async (days: number): Promise<{ deleted: number }> => {
    const response = await adminApi.delete('/api/admin/logs/cleanup', { params: { days } });
    return response.data;
  },
};

// =============================================================================
// Projects API (Construction Domain)
// =============================================================================

export interface Project {
  id: number;
  name: string;
  project_code: string;
  description: string | null;
  tenant_id: number | null;
  manager_id: number | null;
  manager_name: string | null;
  is_active: boolean;
  report_count: number;
  created_at: string;
  updated_at: string;
}

export interface ProjectListResponse {
  projects: Project[];
  total: number;
}

export interface CreateProjectRequest {
  name: string;
  description?: string;
  manager_id?: number;
}

export const projectsApi = {
  list: async (params?: { is_active?: boolean; skip?: number; limit?: number }): Promise<ProjectListResponse> => {
    const response = await adminApi.get('/api/domains/construction/projects', { params });
    return response.data;
  },

  get: async (id: number): Promise<Project> => {
    const response = await adminApi.get(`/api/domains/construction/projects/${id}`);
    return response.data;
  },

  create: async (data: CreateProjectRequest): Promise<Project> => {
    const response = await adminApi.post('/api/domains/construction/projects', data);
    return response.data;
  },

  update: async (id: number, data: Partial<Project>): Promise<Project> => {
    const response = await adminApi.patch(`/api/domains/construction/projects/${id}`, data);
    return response.data;
  },

  archive: async (id: number): Promise<void> => {
    await adminApi.post(`/api/domains/construction/projects/${id}/archive`);
  },

  delete: async (id: number): Promise<void> => {
    await adminApi.delete(`/api/domains/construction/projects/${id}`);
  },

  validateCode: async (code: string): Promise<{ valid: boolean; project_id?: number; project_name?: string }> => {
    const response = await adminApi.get(`/api/domains/construction/validate-code/${code}`);
    return response.data;
  },
};

// =============================================================================
// Prompts API
// =============================================================================

export interface PromptTemplate {
  id: number;
  name: string;
  slug: string;
  domain: string;
  description: string | null;
  system_prompt: string;
  user_prompt_template: string;
  response_schema: Record<string, unknown> | null;
  is_active: boolean;
  is_default: boolean;
  version: number;
  created_at: string;
  updated_at: string;
  created_by: string | null;
}

export interface PromptTemplateListResponse {
  templates: PromptTemplate[];
  total: number;
}

export interface CreatePromptTemplateRequest {
  name: string;
  slug: string;
  domain: string;
  description?: string;
  system_prompt: string;
  user_prompt_template: string;
  response_schema?: Record<string, unknown>;
  is_default?: boolean;
}

export interface UpdatePromptTemplateRequest {
  name?: string;
  description?: string;
  system_prompt?: string;
  user_prompt_template?: string;
  response_schema?: Record<string, unknown>;
  is_active?: boolean;
  is_default?: boolean;
}

export interface ValidateSchemaResponse {
  valid: boolean;
  errors: string[];
  warnings: string[];
  supported_by_gemini: boolean;
}

export interface DomainInfo {
  name: string;
  template_count: number;
}

export const promptsApi = {
  list: async (params?: { domain?: string; is_active?: boolean; skip?: number; limit?: number }): Promise<PromptTemplateListResponse> => {
    const response = await adminApi.get('/api/admin/prompts/templates', { params });
    return response.data;
  },

  get: async (id: number): Promise<PromptTemplate> => {
    const response = await adminApi.get(`/api/admin/prompts/templates/${id}`);
    return response.data;
  },

  getBySlug: async (slug: string): Promise<PromptTemplate> => {
    const response = await adminApi.get(`/api/admin/prompts/templates/slug/${slug}`);
    return response.data;
  },

  create: async (data: CreatePromptTemplateRequest): Promise<PromptTemplate> => {
    const response = await adminApi.post('/api/admin/prompts/templates', data);
    return response.data;
  },

  update: async (id: number, data: UpdatePromptTemplateRequest): Promise<PromptTemplate> => {
    const response = await adminApi.patch(`/api/admin/prompts/templates/${id}`, data);
    return response.data;
  },

  delete: async (id: number): Promise<void> => {
    await adminApi.delete(`/api/admin/prompts/templates/${id}`);
  },

  validateSchema: async (schema: Record<string, unknown>): Promise<ValidateSchemaResponse> => {
    const response = await adminApi.post('/api/admin/prompts/validate-schema', { schema });
    return response.data;
  },

  getDomains: async (): Promise<{ domains: DomainInfo[] }> => {
    const response = await adminApi.get('/api/admin/prompts/domains');
    return response.data;
  },

  getSchemaTemplates: async (): Promise<{ templates: Array<{ id: string; name: string; description: string; domain: string; schema: Record<string, unknown> }> }> => {
    const response = await adminApi.get('/api/admin/prompts/schema-templates');
    return response.data;
  },
};
