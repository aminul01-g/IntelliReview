import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

export function useFeedbackHistory(limit = 20) {
  return useQuery({
    queryKey: ['feedbackHistory', limit],
    queryFn: async () => {
      const { data } = await api.get(`/review_feedback/feedback-history?limit=${limit}`);
      return data;
    }
  });
}
