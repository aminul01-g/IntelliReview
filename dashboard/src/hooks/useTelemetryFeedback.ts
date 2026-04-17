import { useMutation } from '@tanstack/react-query';
import { api } from '@/lib/api';

export interface TelemetryPayload {
  rule_id: string;
  action: 'accept' | 'reject';
  task_id?: string;
  line_number?: number;
}

export function useTelemetryFeedback() {
  return useMutation({
    mutationFn: async (payload: TelemetryPayload) => {
      const response = await api.post('/telemetry/feedback', payload);
      return response.data;
    }
  });
}
