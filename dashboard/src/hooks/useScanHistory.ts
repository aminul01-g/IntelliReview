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

export interface TransformedScanData {
  id: string;
  project_name: string;
  date: string;
  health_score: number;
  technical_debt_hours: number;
  critical_vulnerabilities: number;
  originalAnalysis?: ScanMetadata;
}

export function useScanHistory(page: number, limit: number) {
  return useQuery({
    queryKey: ['scanHistory', page, limit],
    queryFn: async () => {
      try {
        // Backend returns List[AnalysisResponse], transform to expected format
        const response = await api.get<ScanMetadata[]>(`/analysis/history?limit=${limit * (page + 1)}`);
        const data = response.data;
        
        if (!data || data.length === 0) {
          return { data: [], total: 0 };
        }
        
        // Transform to expected format
        const transformedData: TransformedScanData[] = data.slice(page * limit, (page + 1) * limit).map((item: any) => ({
          id: item.analysis_id?.toString?.() || item.id?.toString?.() || 'unknown',
          project_name: item.file_path || item.language || 'Unknown Project',
          date: item.analyzed_at ? new Date(item.analyzed_at).toLocaleDateString() : new Date().toLocaleDateString(),
          health_score: item.metrics?.maintainability_index ? Math.round(item.metrics.maintainability_index) : 85,
          technical_debt_hours: item.metrics?.cognitive_complexity ? Math.round(item.metrics.cognitive_complexity / 10) : 0,
          critical_vulnerabilities: (item.issues || []).filter((issue: any) => issue.severity === 'critical').length || 0,
          originalAnalysis: item,
        }));
        
        return {
          data: transformedData,
          total: data.length
        };
      } catch (error) {
        console.error('Failed to fetch scan history:', error);
        return { data: [], total: 0 };
      }
    }
  });
}

export function useScanReport(scanId: string | null) {
  return useQuery({
    queryKey: ['scanReport', scanId],
    queryFn: async () => {
      if (!scanId) {
        throw new Error('Scan ID is required');
      }
      
      try {
        // Backend returns AnalysisResponse, transform to expected format
        const response = await api.get(`/analysis/history/${scanId}`);
        const data = response.data;
        
        // Safely access properties with fallbacks
        const analyzedAt = data?.analyzed_at ? new Date(data.analyzed_at).toLocaleDateString() : new Date().toLocaleDateString();
        
        // Transform to expected format
        return {
          id: data?.analysis_id?.toString?.() || scanId,
          project_name: data?.file_path || data?.language || 'Unknown',
          date: analyzedAt,
          health_score: data?.metrics?.maintainability_index ? Math.round(data.metrics.maintainability_index) : 85,
          technical_debt_hours: data?.metrics?.cognitive_complexity ? Math.round(data.metrics.cognitive_complexity / 10) : 0,
          critical_vulnerabilities: (data?.issues || []).filter((issue: any) => issue?.severity === 'critical').length || 0,
          details: {
            issues: data?.issues || [],
            metrics: data?.metrics || {},
            language: data?.language || 'Unknown',
            processing_time: data?.processing_time || null,
            status: data?.status || 'Unknown',
            suggestions_count: data?.suggestions_count || 0,
          }
        };
      } catch (error) {
        console.error(`Failed to fetch scan report ${scanId}:`, error);
        throw error;
      }
    },
    enabled: !!scanId
  });
}
