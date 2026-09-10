import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import type { JobStatusOut } from '../types/api';

export function useJobPoll(jobId: string | null | undefined) {
  return useQuery<JobStatusOut>({
    queryKey: ['jobs', jobId],
    queryFn: () => {
      if (!jobId) throw new Error('No jobId provided');
      return api.getJobStatus(jobId);
    },
    enabled: Boolean(jobId),
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return 3000;
      if (data.status === 'completed' || data.status === 'error') {
        return false; // Stop polling
      }
      return 3000;
    },
  });
}
