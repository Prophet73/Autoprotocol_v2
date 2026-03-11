import axios from 'axios';
import { useAuthStore } from '../stores/authStore';
import { API_BASE_URL, getApiBaseUrl } from '../config/api';
import { triggerSSOReauth } from '../utils/tokenExpiry';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add interceptor to include auth token
api.interceptors.request.use((config) => {
  const { token } = useAuthStore.getState();

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

// Handle 401 responses — try refresh token, then SSO re-auth, then login redirect
let isRefreshing = false;
let refreshQueue: Array<{ resolve: (token: string) => void; reject: (err: unknown) => void }> = [];

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      const { refreshToken } = useAuthStore.getState();

      // Try refresh token if available
      if (refreshToken) {
        if (isRefreshing) {
          // Queue this request while refresh is in progress
          return new Promise((resolve, reject) => {
            refreshQueue.push({
              resolve: (token: string) => {
                originalRequest.headers.Authorization = `Bearer ${token}`;
                resolve(api(originalRequest));
              },
              reject,
            });
          });
        }

        originalRequest._retry = true;
        isRefreshing = true;

        try {
          const resp = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });
          const { access_token, refresh_token: newRefresh } = resp.data;
          useAuthStore.getState().setTokens(access_token, newRefresh);

          // Retry queued requests
          refreshQueue.forEach((q) => q.resolve(access_token));
          refreshQueue = [];

          // Retry original request
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return api(originalRequest);
        } catch {
          refreshQueue.forEach((q) => q.reject(error));
          refreshQueue = [];
          // Refresh failed — fall through to logout
        } finally {
          isRefreshing = false;
        }
      }

      // No refresh token or refresh failed — logout
      useAuthStore.getState().logout();

      if (import.meta.env.VITE_SSO_HUB_ENABLED === 'true') {
        triggerSSOReauth();
      } else {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

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
  warnings?: string[];
  can_retry_reports?: boolean;
}

// Meeting report topic (CEO/NOTECH domain)
// NotechQuestion from CEO domain (raw from DB report_json)
export interface NotechQuestion {
  title: string;
  description: string;
  value_points?: string[];
  decision?: string;
  discussion_details?: string[];
  risks?: string[];
}

// Domain report JSON stored in DB (raw LLM output)
// CEO/notech: NotechResult format
// Other domains: generic with meeting_summary, action_items
export interface DomainReportJSON {
  // CEO notech fields
  meeting_topic?: string;
  summary?: string;
  attendees?: string[];
  questions?: NotechQuestion[];
  action_items?: string[];
  // Generic fields
  meeting_summary?: string;
  meeting_type?: string;
  // Other domain-specific fields preserved as-is
  [key: string]: unknown;
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
  meeting_report?: DomainReportJSON;
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
  generate_summary?: boolean;
  // Project linkage for Drop Box workflow
  project_code?: string;
  // Meeting type for domain-specific processing
  meeting_type?: string;
  // Meeting date (optional)
  meeting_date?: string;
  // Email notification (optional)
  notify_emails?: string;
  // Meeting participants (person IDs)
  participant_ids?: number[];
  // Domain for domain-specific processing (construction, hr, dct)
  domain?: string;
  // Private job (hidden from department calendar)
  is_private?: boolean;
}

// Meeting type info from backend
export interface MeetingTypeInfo {
  id: string;
  name: string;
  description?: string;
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
  options: TranscribeOptions = {},
  onProgress?: (percent: number) => void,
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
  if (options.generate_summary) formData.append('generate_summary', 'true');
  // Project code for Drop Box workflow
  if (options.project_code) formData.append('project_code', options.project_code);
  // Domain for domain-specific processing
  if (options.domain) formData.append('domain', options.domain);
  // Meeting type for domain-specific processing
  if (options.meeting_type) formData.append('meeting_type', options.meeting_type);
  // Meeting date
  if (options.meeting_date) formData.append('meeting_date', options.meeting_date);
  // Email notification
  if (options.notify_emails) formData.append('notify_emails', options.notify_emails);
  if (options.is_private) formData.append('is_private', 'true');
  // Meeting participants
  if (options.participant_ids && options.participant_ids.length > 0) {
    formData.append('participant_ids', options.participant_ids.join(','));
  }

  const response = await api.post<JobResponse>('/transcribe', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: onProgress
      ? (e) => {
          const percent = e.total ? Math.round((e.loaded * 100) / e.total) : 0;
          onProgress(percent);
        }
      : undefined,
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

// Download job file with authentication
export async function downloadJobFile(jobId: string, fileType: string): Promise<void> {
  const url = getDownloadUrl(jobId, fileType);
  const token = useAuthStore.getState().token;

  const headers: Record<string, string> = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(url, { headers });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Download failed: ${response.status}`);
  }

  // Get filename from Content-Disposition header or use default
  const contentDisposition = response.headers.get('Content-Disposition');
  let filename = `${fileType}.${fileType === 'tasks' ? 'xlsx' : fileType === 'risk_brief' ? 'pdf' : 'docx'}`;
  if (contentDisposition) {
    const utf8Match = contentDisposition.match(/filename\*=utf-8''([^;]+)/i);
    if (utf8Match) {
      filename = decodeURIComponent(utf8Match[1]);
    } else {
      const match = contentDisposition.match(/filename="?([^"]+)"?/);
      if (match) filename = match[1];
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

// Download all job files as zip with authentication
export async function downloadJobFileAll(jobId: string): Promise<void> {
  const url = getDownloadAllUrl(jobId);
  const token = useAuthStore.getState().token;

  const headers: Record<string, string> = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(url, { headers });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Download failed: ${response.status}`);
  }

  const contentDisposition = response.headers.get('Content-Disposition');
  let filename = `job_${jobId}_files.zip`;
  if (contentDisposition) {
    const utf8Match = contentDisposition.match(/filename\*=utf-8''([^;]+)/i);
    if (utf8Match) {
      filename = decodeURIComponent(utf8Match[1]);
    } else {
      const match = contentDisposition.match(/filename="?([^"]+)"?/);
      if (match) filename = match[1];
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

// History types
export interface JobListItem {
  job_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  created_at: string;
  source_file: string;
  progress_percent: number;
  message?: string;
  has_warnings?: boolean;
  meeting_type?: string;
  meeting_type_name?: string;
}

export interface JobListResponse {
  jobs: JobListItem[];
}

export async function getJobs(limit: number = 50, domain?: string, scope?: 'my' | 'domain'): Promise<JobListResponse> {
  const params = new URLSearchParams({ limit: limit.toString() });
  if (domain) {
    params.append('domain', domain);
  }
  if (scope) {
    params.append('scope', scope);
  }
  const response = await api.get<JobListResponse>(`/transcribe?${params.toString()}`);
  return response.data;
}

export async function cancelJob(jobId: string): Promise<{ success: boolean }> {
  const response = await api.delete(`/transcribe/${jobId}`);
  return response.data;
}

export async function retryReports(jobId: string): Promise<{ success: boolean }> {
  const response = await api.post(`/transcribe/${jobId}/retry-reports`);
  return response.data;
}

// Get available domains from backend
export interface DomainInfo {
  id: string;
  name: string;
  meeting_types_count: number;
}

export async function getDomains(): Promise<DomainInfo[]> {
  const response = await api.get<{ domains: DomainInfo[] }>('/api/domains/');
  return response.data.domains;
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
      message: 'Не удалось проверить код проекта. Попробуйте позже.',
    };
  }
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

// Risk Brief types for interactive display
export interface RiskDriver {
  id: string;
  type: 'root_cause' | 'aggravator' | 'blocker';
  title: string;
  description: string;
  evidence: string;
}

export interface ProjectRisk {
  id: string;
  title: string;
  category: string;
  description: string;
  consequences: string;
  decision?: string;  // Решение с совещания (всегда показывать)
  mitigation?: string;  // Рекомендация ИИ
  probability: number;
  impact: number;
  responsible?: string;
  suggested_responsible?: string;
  deadline?: string;
  is_blocker: boolean;
  drivers: RiskDriver[];
  evidence?: string;
  evidence_timecode?: string;
  confidence: 'high' | 'medium' | 'low';
}

export interface RiskBriefData {
  project_name?: string;
  project_code?: string;
  location?: string;
  overall_status: 'stable' | 'attention' | 'critical';
  executive_summary: string;
  atmosphere: string;
  atmosphere_comment: string;
  risks: ProjectRisk[];
  concerns: ConcernItem[];
  abbreviations: Array<{ abbr: string; full: string }>;
}

// Concern item from RiskBrief
export interface ConcernItem {
  id: string;
  category?: string;
  title: string;
  description: string;
  recommendation?: string;
  related_risk_ids?: string[];
}

// Participant group for display
export interface ParticipantGroup {
  org_name: string;
  persons: string[];
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
  has_summary: boolean;
  filename: string;
  // Risk brief JSON for interactive display
  risk_brief_json?: RiskBriefData;
  // Basic report JSON (meeting_summary, expert_analysis, tasks)
  basic_report_json?: BasicReportData;
  // Meeting participants grouped by organization
  participants?: ParticipantGroup[];
}

// Basic report data from BasicReport JSON
export interface BasicReportData {
  meeting_type?: string;
  meeting_summary?: string;
  expert_analysis?: string;
  tasks?: TaskItem[];
}

// Task item from BasicReport
export interface TaskItem {
  category?: string;
  description: string;
  responsible?: string;
  deadline?: string;
  priority?: 'high' | 'medium' | 'low';
  confidence?: string;
  time_codes?: string[];
  evidence?: string;
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

// Download analytics report with authentication
export async function downloadAnalyticsReport(
  analyticsId: number,
  type: 'main' | 'detailed' | 'transcript' | 'tasks' | 'risk_brief' | 'summary'
): Promise<void> {
  const url = `${getApiBaseUrl()}/api/manager/analytics/${analyticsId}/report/${type}`;
  const token = useAuthStore.getState().token;

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
  const defaultFilenames: Record<string, string> = {
    main: 'report.docx',
    detailed: 'detailed_report.docx',
    transcript: 'transcript.docx',
    risk_brief: 'risk_brief.pdf',
    summary: 'summary.docx',
    tasks: 'tasks.xlsx',
  };
  let filename = defaultFilenames[type] || 'report.docx';
  if (contentDisposition) {
    const utf8Match = contentDisposition.match(/filename\*=utf-8''([^;]+)/i);
    if (utf8Match) {
      filename = decodeURIComponent(utf8Match[1]);
    } else {
      const match = contentDisposition.match(/filename="?([^"]+)"?/);
      if (match) filename = match[1];
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

// =============================================================================
// Project Contractors & Participants
// =============================================================================

export interface Person {
  id: number;
  full_name: string;
  position?: string;
  email?: string;
}

export interface Contractor {
  id: number;
  organization_id: number;
  organization_name: string;
  role: string;
  role_label: string;
  persons: Person[];
}

export interface StandardRole {
  value: string;
  label: string;
}

export async function getProjectContractors(projectCode: string): Promise<Contractor[]> {
  const response = await api.get<Contractor[]>(`/api/manager/projects/${projectCode}/contractors`);
  return response.data;
}

export async function getStandardRoles(): Promise<StandardRole[]> {
  const response = await api.get<StandardRole[]>('/api/manager/roles');
  return response.data;
}

// Create a contractor for project
export async function createProjectContractor(
  projectCode: string,
  data: {
    organization_name: string;
    role: string;
    short_name?: string;
  }
): Promise<Contractor> {
  const response = await api.post<Contractor>(
    `/api/manager/projects/${projectCode}/contractors`,
    data
  );
  return response.data;
}

// Add a person to organization
export async function addPersonToOrganization(
  organizationId: number,
  data: {
    full_name: string;
    position?: string;
    email?: string;
    phone?: string;
  }
): Promise<Person> {
  const response = await api.post<Person>(
    `/api/manager/organizations/${organizationId}/persons`,
    data
  );
  return response.data;
}

// Update a person's name and/or position
export async function updatePerson(
  personId: number,
  data: { full_name?: string; position?: string }
): Promise<Person> {
  const response = await api.patch<Person>(
    `/api/manager/persons/${personId}`,
    data
  );
  return response.data;
}

// Delete (soft) a person
export async function deletePerson(personId: number): Promise<void> {
  await api.delete(`/api/manager/persons/${personId}`);
}

// Update organization name
export async function updateOrganization(
  orgId: number,
  data: { name?: string; short_name?: string }
): Promise<void> {
  await api.patch(`/api/manager/organizations/${orgId}`, data);
}

// Delete a contractor from project
export async function deleteContractor(
  projectCode: string,
  contractorId: number
): Promise<void> {
  await api.delete(`/api/manager/projects/${projectCode}/contractors/${contractorId}`);
}

