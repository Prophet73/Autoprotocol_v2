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

  setActiveDomain: async (domain: string): Promise<CurrentUser> => {
    const response = await adminApi.post('/auth/me/domain', { domain });
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
    it: number;
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
// Comprehensive Stats API (New)
// =============================================================================

export interface StatsFilters {
  date_from?: string;
  date_to?: string;
  domain?: string;
  meeting_type?: string;
  project_id?: number;
  user_id?: number;
}

export interface KPIStats {
  total_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  pending_jobs: number;
  processing_jobs: number;
  success_rate: number;
  total_processing_hours: number;
  avg_processing_minutes: number;
  total_audio_hours: number;
  total_cost_usd: number;
  avg_cost_per_job: number;
}

export interface MeetingTypeStats {
  meeting_type: string;
  name: string;
  count: number;
  completed: number;
  failed: number;
  success_rate: number;
  total_processing_seconds: number;
  total_audio_seconds: number;
}

export interface DomainStats {
  domain: string;
  display_name: string;
  total_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  success_rate: number;
  total_processing_hours: number;
  total_audio_hours: number;
  total_cost_usd: number;
  meeting_types: MeetingTypeStats[];
}

export interface DomainsBreakdown {
  domains: DomainStats[];
}

export interface UserActivityStats {
  user_id: number;
  email: string;
  full_name: string | null;
  role: string;
  total_jobs: number;
  completed_jobs: number;
  domains_used: string[];
  last_activity: string | null;
}

export interface UsersStats {
  total_users: number;
  active_users: number;
  by_role: Record<string, number>;
  by_domain: Record<string, number>;
  top_users: UserActivityStats[];
}

export interface CostStats {
  total_input_tokens: number;
  total_output_tokens: number;
  total_cost_usd: number;
  avg_cost_per_job: number;
  by_domain: Record<string, number>;
  input_price_per_million: number;
  output_price_per_million: number;
}

export interface TimelinePoint {
  date: string;
  jobs: number;
  completed: number;
  failed: number;
}

export interface TimelineStats {
  points: TimelinePoint[];
  period: string;
  total_days: number;
}

export interface ErrorStats {
  total_errors: number;
  error_rate: number;
  by_stage: Record<string, number>;
  by_domain: Record<string, number>;
  recent_errors: Array<{
    id: number;
    job_id: string;
    error_message: string;
    error_stage: string;
    created_at: string;
  }>;
}

export interface ArtifactsStats {
  transcripts_generated: number;
  tasks_generated: number;
  reports_generated: number;
  analysis_generated: number;
  transcript_rate: number;
  tasks_rate: number;
  report_rate: number;
  analysis_rate: number;
}

export interface FullDashboardResponse {
  overview: KPIStats;
  domains: DomainsBreakdown;
  users: UsersStats;
  costs: CostStats;
  timeline: TimelineStats;
  artifacts: ArtifactsStats;
  errors: ErrorStats;
  filters_applied: StatsFilters;
  generated_at: string;
}

export interface DomainStatsResponse {
  domain: DomainStats;
  projects?: {
    projects: Array<{
      project_id: number;
      project_name: string;
      project_code: string;
      total_jobs: number;
      completed_jobs: number;
      failed_jobs: number;
      success_rate: number;
      total_processing_hours: number;
      total_audio_hours: number;
      last_activity: string | null;
    }>;
    total_projects: number;
  };
  timeline: TimelineStats;
  errors: ErrorStats;
  filters_applied: StatsFilters;
  generated_at: string;
}

export interface UsersStatsResponse {
  users: UsersStats;
  timeline: TimelineStats;
  filters_applied: StatsFilters;
  generated_at: string;
}

export interface CostStatsResponse {
  costs: CostStats;
  timeline: Array<{ date: string; cost: number }>;
  filters_applied: StatsFilters;
  generated_at: string;
}

export interface DomainInfo {
  id: string;
  name: string;
  meeting_types: Array<{ id: string; name: string }>;
}

export const comprehensiveStatsApi = {
  getDashboard: async (filters?: StatsFilters): Promise<FullDashboardResponse> => {
    const response = await adminApi.get('/api/admin/stats/dashboard', { params: filters });
    return response.data;
  },

  getDomains: async (): Promise<{ domains: DomainInfo[] }> => {
    const response = await adminApi.get('/api/admin/stats/domains');
    return response.data;
  },

  getDomainStats: async (domainId: string, filters?: StatsFilters): Promise<DomainStatsResponse> => {
    const response = await adminApi.get(`/api/admin/stats/domain/${domainId}`, { params: filters });
    return response.data;
  },

  getUsersStats: async (filters?: StatsFilters): Promise<UsersStatsResponse> => {
    const response = await adminApi.get('/api/admin/stats/users', { params: filters });
    return response.data;
  },

  getCostsStats: async (filters?: StatsFilters): Promise<CostStatsResponse> => {
    const response = await adminApi.get('/api/admin/stats/costs', { params: filters });
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
  project_code?: string;  // 4-digit code, auto-generated if not provided
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

// =============================================================================
// Jobs API (Admin)
// =============================================================================

export interface AdminJobInfo {
  job_id: string;
  status: string;
  created_at: string | null;
  updated_at: string | null;
  source_file: string | null;
  progress_percent: number;
  current_stage: string | null;
  message: string | null;
  project_code: string | null;
  uploader_email: string | null;
  error: string | null;
}

export interface AdminJobsListResponse {
  jobs: AdminJobInfo[];
}

export const jobsApi = {
  list: async (limit: number = 100): Promise<AdminJobsListResponse> => {
    const response = await adminApi.get('/api/admin/jobs', { params: { limit } });
    return response.data;
  },

  cancel: async (jobId: string): Promise<{ success: boolean; message: string }> => {
    const response = await adminApi.delete(`/api/admin/jobs/${jobId}`);
    return response.data;
  },
};

// =============================================================================
// Prompts API
// =============================================================================

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
