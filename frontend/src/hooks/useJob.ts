import { useQuery } from '@tanstack/react-query';
import { getJobStatus, getJobResult } from '../api/client';
import type { JobStatusResponse, JobResultResponse } from '../api/client';

export function useJobStatus(jobId: string | undefined, enabled = true) {
  return useQuery<JobStatusResponse>({
    queryKey: ['job-status', jobId],
    queryFn: () => getJobStatus(jobId!),
    enabled: !!jobId && enabled,
    refetchInterval: (query) => {
      const data = query.state.data;
      // Stop polling when completed or failed
      if (data?.status === 'completed' || data?.status === 'failed') {
        return false;
      }
      // Poll every 2 seconds while processing
      return 2000;
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
