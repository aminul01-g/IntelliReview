import { useQuery, useMutation } from '@tanstack/react-query';
import { api } from '@/lib/api';

export interface AnalysisTaskResult {
  status: 'pending' | 'processing' | 'completed' | 'failed';
  task_id: string;
  result?: any;
  progress?: number; 
}


// Submits a diff/code snippet for analysis using the correct backend endpoint
export function useSubmitAnalysis() {
  return useMutation({
    mutationFn: async (payload: { diff: string }) => {
      // Backend expects { diff: string }
      const response = await api.post<{ task_id: string }>('/analysis/diff-review', payload);
      return response.data;
    }
  })
}

// Polls the status of an analysis task using the correct backend endpoint
export function useAnalysisTaskStatus(taskId: string | null) {
  return useQuery<AnalysisTaskResult>({
    queryKey: ['taskStatus', taskId],
    queryFn: async () => {
      if (!taskId) throw new Error('No taskId');
      // Use the correct endpoint for diff/code snippet analysis
      const response = await api.get<AnalysisTaskResult>(`/analysis/diff-review/status/${taskId}`);
      return response.data;
    },
    enabled: !!taskId,
    refetchInterval: (query: any) => {
      const status = query.state.data?.status;
      if (status === 'completed' || status === 'failed' || status === 'SUCCESS' || status === 'FAILURE') return false;
      return 2000;
    },
  });
}
