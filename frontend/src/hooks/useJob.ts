import { useQuery } from '@tanstack/react-query';
import { getJobStatus, getJobResult } from '../api/client';
import type { JobStatusResponse, JobResultResponse } from '../api/client';

const POLL_START_TIMES = new Map<string, number>();

export function useJobStatus(jobId: string | undefined, enabled = true) {
  return useQuery<JobStatusResponse>({
    queryKey: ['job-status', jobId],
    queryFn: () => {
      if (jobId && !POLL_START_TIMES.has(jobId)) {
        POLL_START_TIMES.set(jobId, Date.now());
      }
      return getJobStatus(jobId!);
    },
    enabled: !!jobId && enabled,
    refetchInterval: (query) => {
      const data = query.state.data;
      // Stop polling when completed or failed
      if (data?.status === 'completed' || data?.status === 'failed') {
        if (jobId) POLL_START_TIMES.delete(jobId);
        return false;
      }
      // Exponential backoff: 2s for first 5 min, then 5s up to 10 min, then 10s
      const startTime = jobId ? POLL_START_TIMES.get(jobId) : undefined;
      const elapsed = startTime ? Date.now() - startTime : 0;

      if (elapsed < 5 * 60 * 1000) return 2000;   // first 5 min → 2s
      if (elapsed < 10 * 60 * 1000) return 5000;   // 5–10 min → 5s
      return 10000;                                  // 10+ min → 10s
    },
  });
}

export function useJobResult(jobId: string | undefined, enabled = true) {
  return useQuery<JobResultResponse>({
    queryKey: ['job-result', jobId],
    queryFn: () => getJobResult(jobId!),
    enabled: !!jobId && enabled,
  });
}
