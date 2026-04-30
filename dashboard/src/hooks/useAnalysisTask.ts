import { useQuery, useMutation } from '@tanstack/react-query';
import { api } from '@/lib/api';

export interface AnalysisTaskResult {
  status: 'PENDING' | 'processing' | 'SUCCESS' | 'FAILURE' | 'completed' | 'failed';
  task_id?: string;
  result?: any;
  info?: string;
  error?: string;
  fallback?: boolean;
}

/**
 * Detect whether the input looks like a unified diff (git diff output)
 * or raw code. Used to route to the correct backend endpoint.
 */
export function isDiffFormat(input: string): boolean {
  const trimmed = input.trim();
  return (
    trimmed.startsWith('diff --git') ||
    trimmed.startsWith('--- a/') ||
    trimmed.startsWith('+++ b/') ||
    /^@@\s+-\d+/.test(trimmed) ||
    // Multiple lines starting with +/- after a @@ header
    (trimmed.includes('\n@@ ') && (trimmed.includes('\n+') || trimmed.includes('\n-')))
  );
}

/**
 * Guess the programming language from a filename extension or code content.
 */
export function guessLanguage(code: string, filename?: string): string {
  if (filename) {
    const ext = filename.split('.').pop()?.toLowerCase();
    const map: Record<string, string> = {
      py: 'python', js: 'javascript', jsx: 'javascript',
      ts: 'javascript', tsx: 'javascript', java: 'java',
      c: 'c', cpp: 'cpp', cc: 'cpp', h: 'c', hpp: 'cpp',
    };
    if (ext && map[ext]) return map[ext];
  }
  // Heuristic detection from code content
  if (/\bdef\s+\w+\s*\(/.test(code) || /\bimport\s+\w+/.test(code) || /\bprint\s*\(/.test(code)) return 'python';
  if (/\bfunction\s+\w+/.test(code) || /\bconst\s+\w+\s*=/.test(code) || /\bconsole\.log/.test(code)) return 'javascript';
  if (/\bpublic\s+class\b/.test(code) || /\bSystem\.out\.print/.test(code)) return 'java';
  if (/\b#include\s*</.test(code) || /\bint\s+main\s*\(/.test(code)) return 'cpp';
  return 'python'; // Default fallback
}

// ─── Diff Mode: Submit to /analysis/diff-review ────────────────────────

export function useSubmitDiffAnalysis() {
  return useMutation({
    mutationFn: async (payload: { diff: string }) => {
      const response = await api.post<{ task_id: string }>('/analysis/diff-review', payload);
      return response.data;
    }
  });
}

export function useDiffTaskStatus(taskId: string | null) {
  return useQuery<AnalysisTaskResult>({
    queryKey: ['diffTaskStatus', taskId],
    queryFn: async () => {
      if (!taskId) throw new Error('No taskId');
      const response = await api.get<AnalysisTaskResult>(`/analysis/diff-review/status/${taskId}`);
      return response.data;
    },
    enabled: !!taskId,
    refetchInterval: (query: any) => {
      const status = query.state.data?.status;
      if (status === 'SUCCESS' || status === 'FAILURE' || status === 'completed' || status === 'failed') return false;
      return 2000;
    },
  });
}

// ─── Snippet Mode: Submit to /analysis/analyze (synchronous) ───────────

export function useSubmitSnippetAnalysis() {
  return useMutation({
    mutationFn: async (payload: { code: string; language: string; filename: string }) => {
      const response = await api.post('/analysis/analyze', payload);
      return response.data;
    }
  });
}

// ─── Unified hook (backward-compatible) ────────────────────────────────

export function useSubmitAnalysis() {
  return useMutation({
    mutationFn: async (payload: { diff: string }) => {
      const response = await api.post<{ task_id: string }>('/analysis/diff-review', payload);
      return response.data;
    }
  });
}

export function useAnalysisTaskStatus(taskId: string | null) {
  return useQuery<AnalysisTaskResult>({
    queryKey: ['taskStatus', taskId],
    queryFn: async () => {
      if (!taskId) throw new Error('No taskId');
      const response = await api.get<AnalysisTaskResult>(`/analysis/diff-review/status/${taskId}`);
      return response.data;
    },
    enabled: !!taskId,
    refetchInterval: (query: any) => {
      const status = query.state.data?.status;
      if (status === 'SUCCESS' || status === 'FAILURE' || status === 'completed' || status === 'failed') return false;
      return 2000;
    },
  });
}
