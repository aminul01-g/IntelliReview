import React from 'react';
import { useFeedbackHistory } from '@/hooks/useFeedbackHistory';

export function FeedbackHistory() {
  const { data, isLoading, error } = useFeedbackHistory();

  return (
    <div className="max-w-3xl mx-auto p-8">
      <h1 className="text-2xl font-bold mb-4">Feedback History</h1>
      {isLoading && <div>Loading...</div>}
      {error && <div className="text-red-500">Error loading feedback history.</div>}
      {data && (
        <div className="overflow-x-auto">
          <table className="min-w-full border border-border rounded-md">
            <thead>
              <tr className="bg-muted text-xs uppercase text-muted-foreground">
                <th className="px-4 py-2 text-left">ID</th>
                <th className="px-4 py-2 text-left">Finding ID</th>
                <th className="px-4 py-2 text-left">Action</th>
                <th className="px-4 py-2 text-left">Rule Type</th>
                <th className="px-4 py-2 text-left">Accepted</th>
              </tr>
            </thead>
            <tbody>
              {data.results?.length === 0 && (
                <tr><td colSpan={5} className="text-center py-4 text-muted-foreground">No feedback history found.</td></tr>
              )}
              {data.results?.map((fb: any) => (
                <tr key={fb.id} className="border-t border-border text-sm">
                  <td className="px-4 py-2">{fb.id}</td>
                  <td className="px-4 py-2">{fb.finding_id}</td>
                  <td className="px-4 py-2">{fb.action}</td>
                  <td className="px-4 py-2">{fb.rule_type}</td>
                  <td className="px-4 py-2">{fb.accepted ? 'Yes' : 'No'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
