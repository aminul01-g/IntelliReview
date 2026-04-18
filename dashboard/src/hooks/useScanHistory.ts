import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

export interface ScanMetadata {
  analysis_id: number;
  status: string;
  language: string;
  file_path?: string;
  original_code?: string;
  issues: any[];
  metrics: any;
  suggestions_count: number;
  analyzed_at: string;
  processing_time?: number;
}

export function useScanHistory(page: number, limit: number) {
  return useQuery({
    queryKey: ['scanHistory', page, limit],
    queryFn: async () => {
      // Backend returns List[AnalysisResponse], transform to expected format
      const response = await api.get<ScanMetadata[]>(`/analysis/history?limit=${limit * (page + 1)}`);
      const data = response.data;
      
      // Transform to expected format
      const transformedData = data.slice(page * limit, (page + 1) * limit).map(item => ({
        id: item.analysis_id.toString(),
        project_name: item.file_path || item.language || 'Unknown',
        date: new Date(item.analyzed_at).toLocaleDateString(),
        health_score: item.metrics?.maintainability_index ? Math.round(item.metrics.maintainability_index) : 85,
        technical_debt_hours: item.metrics?.cognitive_complexity ? Math.round(item.metrics.cognitive_complexity / 10) : 0,
        critical_vulnerabilities: item.issues?.filter(issue => issue.severity === 'critical').length || 0,
      }));
      
      return {
        data: transformedData,
        total: data.length
      };
    }
  });
}

export function useScanReport(scanId: string | null) {
  return useQuery({
    queryKey: ['scanReport', scanId],
    queryFn: async () => {
      // Backend returns AnalysisResponse, transform to expected format
      const response = await api.get(`/analysis/history/${scanId}`);
      const data = response.data;
      
      // Transform to expected format
      return {
        id: data.analysis_id.toString(),
        project_name: data.file_path || data.language || 'Unknown',
        date: new Date(data.analyzed_at).toLocaleDateString(),
        health_score: data.metrics?.maintainability_index ? Math.round(data.metrics.maintainability_index) : 85,
        technical_debt_hours: data.metrics?.cognitive_complexity ? Math.round(data.metrics.cognitive_complexity / 10) : 0,
        critical_vulnerabilities: data.issues?.filter((issue: any) => issue.severity === 'critical').length || 0,
        details: {
          issues: data.issues || [],
          metrics: data.metrics || {},
          language: data.language,
          processing_time: data.processing_time
        }
      };
    },
    enabled: !!scanId
  });
}
