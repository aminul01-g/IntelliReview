import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

export interface ScanMetadata {
  id: string;
  project_name: string;
  date: string;
  health_score: number;
  technical_debt_hours: number;
  critical_vulnerabilities: number;
}

export function useScanHistory(page: number, limit: number) {
  return useQuery({
    queryKey: ['scanHistory', page, limit],
    queryFn: async () => {
      // Mocking response structure or fetching from actual Postgres endpoint
      const response = await api.get<{ data: ScanMetadata[], total: number }>(`/analysis/history?page=${page}&limit=${limit}`);
      return response.data;
    }
  });
}

export function useScanReport(scanId: string | null) {
  return useQuery({
    queryKey: ['scanReport', scanId],
    queryFn: async () => {
      // Fetches full JSON report from MongoDB
      const response = await api.get(`/analysis/report/${scanId}`);
      return response.data;
    },
    enabled: !!scanId
  });
}
