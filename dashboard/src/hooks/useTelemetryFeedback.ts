import { useMutation } from '@tanstack/react-query';
import { api } from '@/lib/api';

export interface TelemetryPayload {
  suggestion_id: string;
  rule_type: string;
  action: 'accept' | 'reject';
  task_id?: string;
  line_number?: number;
}

export function useTelemetryFeedback() {
  return useMutation({
    mutationFn: async (payload: TelemetryPayload) => {
      // Map action to accepted field (accept=true, reject=false)
      const response = await api.post('/feedback/submit', {
        suggestion_id: payload.suggestion_id,
        accepted: payload.action === 'accept',
        issue_type: payload.rule_type,
        comment: ''
      });
      return response.data;
    }
  });
}
