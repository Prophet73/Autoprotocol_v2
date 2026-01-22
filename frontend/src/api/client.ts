import axios from 'axios';
import { getGuestId } from '../utils/guestId';
import { useAuthStore } from '../stores/authStore';
import { API_BASE_URL, getApiBaseUrl } from '../config/api';

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
  generate_risk_brief?: boolean;
  // Project linkage for Drop Box workflow
  project_code?: string;
  // Meeting type for domain-specific processing
  meeting_type?: string;
  // Meeting date (optional)
  meeting_date?: string;
  // Email notification (optional)
  notify_emails?: string;
}

// Meeting type info from backend
export interface MeetingTypeInfo {
  id: string;
  name: string;
  default?: boolean;
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
  if (options.generate_risk_brief) formData.append('generate_risk_brief', 'true');
  // Project code for Drop Box workflow
  if (options.project_code) formData.append('project_code', options.project_code);
  // Meeting type for domain-specific processing
  if (options.meeting_type) formData.append('meeting_type', options.meeting_type);
  // Meeting date
  if (options.meeting_date) formData.append('meeting_date', options.meeting_date);
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
  return `${getApiBaseUrl()}/transcribe/${jobId}/download/${fileType}`;
}

export function getDownloadAllUrl(jobId: string): string {
  return `${getApiBaseUrl()}/transcribe/${jobId}/download/all`;
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

// Get meeting types for a domain
export async function getMeetingTypes(domain: string): Promise<MeetingTypeInfo[]> {
  const response = await api.get<MeetingTypeInfo[]>(`/api/domains/${domain}/meeting-types`);
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

// Manager Dashboard API (Autoprotokol style)
export interface ManagerDashboardKPI {
  total_jobs: number;
  attention_jobs: number;
  critical_jobs: number;
}

export interface CalendarEvent {
  id: number;
  analytics_id: number | null;
  title: string;
  date: string;
  status: 'critical' | 'attention' | 'stable';
  project_id: number;
  project_code: string;
  project_name: string;
}

export interface AttentionItem {
  id: number;
  analytics_id: number;
  problem_text: string;
  status: 'new' | 'done';
  severity: 'critical' | 'attention';
  source_file: string;
  project_name: string;
  created_at: string;
}

export interface ActivityFeedItem {
  id: number;
  title: string;
  project_name: string;
  status: 'critical' | 'attention' | 'stable';
  created_at: string;
}

export interface ProjectHealth {
  id: number;
  name: string;
  project_code: string;
  health: 'critical' | 'attention' | 'stable';
  total_reports: number;
  open_issues: number;
}

export interface ManagerDashboardView {
  kpi: ManagerDashboardKPI;
  calendar_events: CalendarEvent[];
  attention_items: AttentionItem[];
  activity_feed: ActivityFeedItem[];
  projects_health: ProjectHealth[];
  pulse_chart: {
    labels: string[];
    critical: number[];
    attention: number[];
    stable: number[];
  };
}

// Dynamic indicator in Autoprotocol format
export interface DynamicIndicator {
  indicator_name: string;
  status: string;  // "Критический", "Есть риски", "В норме"
  comment: string;
}

export interface AnalyticsDetail {
  id: number;
  summary: string;
  status: 'critical' | 'attention' | 'stable';
  key_indicators: DynamicIndicator[];
  challenges: Array<{ text: string; recommendation: string }>;
  achievements: string[];
  toxicity_level: number;
  toxicity_details: string;
  report_files: {
    main?: string;
    detailed?: string;
    transcript?: string;
    tasks?: string;
    risk_brief?: string;
  };
  // Flags for download buttons (Autoprotocol format)
  has_main_report: boolean;
  has_detailed_report: boolean;
  has_transcript: boolean;
  has_tasks: boolean;
  has_risk_brief: boolean;
  filename: string;
}

export async function getManagerDashboardView(
  projectId?: number,
  startDate?: string,
  endDate?: string
): Promise<ManagerDashboardView> {
  const params = new URLSearchParams();
  if (projectId) params.append('project_id', projectId.toString());
  if (startDate) params.append('start_date', startDate);
  if (endDate) params.append('end_date', endDate);

  const query = params.toString() ? `?${params.toString()}` : '';
  const response = await api.get<ManagerDashboardView>(
    `/api/manager/dashboard-view${query}`
  );
  return response.data;
}

export async function getAnalyticsDetail(analyticsId: number): Promise<AnalyticsDetail> {
  const response = await api.get<AnalyticsDetail>(`/api/manager/analytics/${analyticsId}`);
  return response.data;
}

export async function updateProblemStatus(
  problemId: number,
  status: 'new' | 'done'
): Promise<{ success: boolean }> {
  const response = await api.post('/api/manager/problem/status', {
    problem_id: problemId,
    status,
  });
  return response.data;
}

export function getAnalyticsReportUrl(
  analyticsId: number,
  type: 'main' | 'detailed' | 'transcript' | 'tasks' | 'risk_brief'
): string {
  return `${getApiBaseUrl()}/api/manager/analytics/${analyticsId}/report/${type}`;
}

// Download analytics report with authentication
export async function downloadAnalyticsReport(
  analyticsId: number,
  type: 'main' | 'detailed' | 'transcript' | 'tasks' | 'risk_brief'
): Promise<void> {
  const url = getAnalyticsReportUrl(analyticsId, type);
  const token = localStorage.getItem('token');

  const response = await fetch(url, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error(`Download failed: ${response.status}`);
  }

  // Get filename from Content-Disposition header or use default
  const contentDisposition = response.headers.get('Content-Disposition');
  let filename = type === 'main'
    ? 'report.docx'
    : type === 'detailed'
    ? 'detailed_report.docx'
    : type === 'transcript'
    ? 'transcript.docx'
    : type === 'risk_brief'
    ? 'risk_brief.pdf'
    : 'tasks.xlsx';
  if (contentDisposition) {
    const match = contentDisposition.match(/filename="?([^"]+)"?/);
    if (match) {
      filename = match[1];
    }
  }

  // Create blob and trigger download
  const blob = await response.blob();
  const blobUrl = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = blobUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(blobUrl);
}

export async function downloadAnalyticsReportAll(analyticsId: number): Promise<void> {
  const url = `${getApiBaseUrl()}/api/manager/analytics/${analyticsId}/report/all`;
  const token = localStorage.getItem('token');

  const response = await fetch(url, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error(`Download failed: ${response.status}`);
  }

  const contentDisposition = response.headers.get('Content-Disposition');
  let filename = `analytics_${analyticsId}_files.zip`;
  if (contentDisposition) {
    const match = contentDisposition.match(/filename="?([^"]+)"?/);
    if (match) {
      filename = match[1];
    }
  }

  const blob = await response.blob();
  const blobUrl = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = blobUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(blobUrl);
}
