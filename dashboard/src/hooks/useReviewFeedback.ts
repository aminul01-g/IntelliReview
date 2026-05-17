import { useMutation } from '@tanstack/react-query';
import { api } from '@/lib/api';

export function useReviewFeedback() {
  // For request better fix
  const requestBetterFix = useMutation({
    mutationFn: async (payload: any) => {
      const { data } = await api.post('/review-feedback/request-better-fix', payload);
      return data;
    }
  });

  // For ignore pattern
  const ignorePattern = useMutation({
    mutationFn: async (payload: any) => {
      const { data } = await api.post('/review-feedback/ignore-pattern', payload);
      return data;
    }
  });

  return { requestBetterFix, ignorePattern };
}
