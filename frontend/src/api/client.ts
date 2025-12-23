import axios from 'axios';
import { getGuestId } from '../utils/guestId';
import { useAuthStore } from '../stores/authStore';

// In dev mode, Vite proxy handles /transcribe -> localhost:8000
// In production, set VITE_API_URL to the backend URL
const API_BASE_URL = import.meta.env.VITE_API_URL || '';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add interceptor to include auth token or guest ID
api.interceptors.request.use((config) => {
  const { token } = useAuthStore.getState();

  if (token) {
    // Authenticated user - use Bearer token
    config.headers.Authorization = `Bearer ${token}`;
  } else {
    // Anonymous user - use guest ID
    config.headers['X-Guest-ID'] = getGuestId();
  }

  return config;
});

// Types
export interface JobResponse {
  job_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  created_at: string;
  message?: string;
}

export interface JobStatusResponse {
  job_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  current_stage?: string;
  progress_percent: number;
  message?: string;
  created_at: string;
  updated_at?: string;
  completed_at?: string;
  error?: string;
}

export interface JobResultResponse {
  job_id: string;
  status: 'completed';
  source_file: string;
  processing_time_seconds: number;
  segment_count: number;
  language_distribution: Record<string, number>;
  output_files: Record<string, string>;
  completed_at: string;
}

export interface TranscribeOptions {
  languages?: string;
  skip_diarization?: boolean;
  skip_translation?: boolean;
  skip_emotions?: boolean;
  generate_transcript?: boolean;
  generate_tasks?: boolean;
  generate_report?: boolean;
  generate_analysis?: boolean;
  // Project linkage for Drop Box workflow
  project_code?: string;
  // Email notification (optional)
  notify_emails?: string;
}

// Project code validation response
export interface ProjectCodeValidation {
  valid: boolean;
  message: string;
  project_id?: number;
  project_name?: string;
  tenant_id?: number;
  domain_type?: string;
}

// API functions
export async function createTranscription(
  file: File,
  options: TranscribeOptions = {}
): Promise<JobResponse> {
  const formData = new FormData();
  formData.append('file', file);

  // Add options
  if (options.languages) formData.append('languages', options.languages);
  if (options.skip_diarization) formData.append('skip_diarization', 'true');
  if (options.skip_translation) formData.append('skip_translation', 'true');
  if (options.skip_emotions) formData.append('skip_emotions', 'true');
  if (options.generate_transcript) formData.append('generate_transcript', 'true');
  if (options.generate_tasks) formData.append('generate_tasks', 'true');
  if (options.generate_report) formData.append('generate_report', 'true');
  if (options.generate_analysis) formData.append('generate_analysis', 'true');
  // Project code for Drop Box workflow
  if (options.project_code) formData.append('project_code', options.project_code);
  // Email notification
  if (options.notify_emails) formData.append('notify_emails', options.notify_emails);

  const response = await api.post<JobResponse>('/transcribe', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}

export async function getJobStatus(jobId: string): Promise<JobStatusResponse> {
  const response = await api.get<JobStatusResponse>(`/transcribe/${jobId}/status`);
  return response.data;
}

export async function getJobResult(jobId: string): Promise<JobResultResponse> {
  const response = await api.get<JobResultResponse>(`/transcribe/${jobId}`);
  return response.data;
}

export function getDownloadUrl(jobId: string, fileType: string): string {
  const base = API_BASE_URL || window.location.origin;
  return `${base}/transcribe/${jobId}/download/${fileType}`;
}

// History types
export interface JobListItem {
  job_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  created_at: string;
  source_file: string;
  progress_percent: number;
  message?: string;
}

export interface JobListResponse {
  jobs: JobListItem[];
}

export async function getJobs(limit: number = 50): Promise<JobListResponse> {
  const response = await api.get<JobListResponse>(`/transcribe?limit=${limit}`);
  return response.data;
}

export async function cancelJob(jobId: string): Promise<{ success: boolean }> {
  const response = await api.delete(`/transcribe/${jobId}`);
  return response.data;
}

// Project code validation for Drop Box workflow
export async function validateProjectCode(code: string): Promise<ProjectCodeValidation> {
  try {
    const response = await api.get<ProjectCodeValidation>(
      `/api/domains/construction/validate-code/${code}`
    );
    return response.data;
  } catch (error) {
    // Handle 404 or other errors
    return {
      valid: false,
      message: 'Project code not found',
    };
  }
}

// Manager dashboard API
export interface ProjectSummary {
  id: number;
  name: string;
  project_code: string;
  is_active: boolean;
  total_reports: number;
  completed_reports: number;
  pending_reports: number;
  failed_reports: number;
  open_risks: number;
  last_report_date: string | null;
}

export interface DashboardData {
  total_reports: number;
  by_project: Record<number, { total: number; reports: Array<{ id: number; title: string; created_at: string }> }>;
  timeline: Array<{
    id: number;
    project_id: number;
    title: string;
    meeting_date: string | null;
    created_at: string | null;
  }>;
  speaker_stats: Record<string, {
    total_time: number;
    appearances: number;
    emotions: Record<string, number>;
  }>;
}

export async function getMyProjects(): Promise<ProjectSummary[]> {
  const response = await api.get<ProjectSummary[]>('/api/domains/construction/my-projects');
  return response.data;
}

export async function getProjectDashboard(
  projectId: number,
  dateFrom?: string,
  dateTo?: string
): Promise<DashboardData> {
  const params = new URLSearchParams();
  if (dateFrom) params.append('date_from', dateFrom);
  if (dateTo) params.append('date_to', dateTo);

  const query = params.toString() ? `?${params.toString()}` : '';
  const response = await api.get<DashboardData>(
    `/api/domains/construction/projects/${projectId}/dashboard${query}`
  );
  return response.data;
}
