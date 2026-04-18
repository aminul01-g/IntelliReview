import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

export function useAnalysisHistory(limit = 20) {
  return useQuery(['analysisHistory', limit], async () => {
    const { data } = await api.get(`/analysis/history?limit=${limit}`);
    return data;
  });
}
