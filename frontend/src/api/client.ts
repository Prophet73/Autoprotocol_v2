import axios from 'axios';

// In dev mode, Vite proxy handles /transcribe -> localhost:8000
// In production, set VITE_API_URL to the backend URL
const API_BASE_URL = import.meta.env.VITE_API_URL || '';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
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
