import { useQuery, useMutation } from '@tanstack/react-query';
import { api } from '@/lib/api';

export interface AnalysisTaskResult {
  status: 'pending' | 'processing' | 'completed' | 'failed';
  task_id: string;
  result?: any;
  progress?: number; 
}

export function useSubmitAnalysis() {
  return useMutation({
    mutationFn: async (payload: { diff: string, project: string }) => {
      const response = await api.post<{ task_id: string }>('/analysis/submit', payload);
      return response.data;
    }
  })
}

export function useAnalysisTaskStatus(taskId: string | null) {
  return useQuery<AnalysisTaskResult>({
    queryKey: ['taskStatus', taskId],
    queryFn: async () => {
      const response = await api.get<AnalysisTaskResult>(`/analysis/task/${taskId}`);
      return response.data;
    },
    enabled: !!taskId,
    refetchInterval: (query: any) => {
      const status = query.state.data?.status;
      if (status === 'completed' || status === 'failed') return false;
      return 2000; 
    },
  });
}
