import React from 'react';
import { useAnalysisHistory } from '@/hooks/useAnalysisHistory';

export function AnalysisHistory() {
  const { data, isLoading, error } = useAnalysisHistory();

  return (
    <div className="max-w-4xl mx-auto p-8">
      <h1 className="text-2xl font-bold mb-4">Analysis History</h1>
      {isLoading && <div>Loading...</div>}
      {error && <div className="text-red-500">Error loading analysis history.</div>}
      {data && (
        <div className="overflow-x-auto">
          <table className="min-w-full border border-border rounded-md">
            <thead>
              <tr className="bg-muted text-xs uppercase text-muted-foreground">
                <th className="px-4 py-2 text-left">ID</th>
                <th className="px-4 py-2 text-left">File Path</th>
                <th className="px-4 py-2 text-left">Language</th>
                <th className="px-4 py-2 text-left">Status</th>
                <th className="px-4 py-2 text-left">Analyzed At</th>
                <th className="px-4 py-2 text-left">Issues</th>
              </tr>
            </thead>
            <tbody>
              {data.length === 0 && (
                <tr><td colSpan={6} className="text-center py-4 text-muted-foreground">No analysis history found.</td></tr>
              )}
              {data.map((item: any) => (
                <tr key={item.analysis_id} className="border-t border-border text-sm">
                  <td className="px-4 py-2">{item.analysis_id}</td>
                  <td className="px-4 py-2">{item.file_path}</td>
                  <td className="px-4 py-2">{item.language}</td>
                  <td className="px-4 py-2">{item.status}</td>
                  <td className="px-4 py-2">{item.analyzed_at ? new Date(item.analyzed_at).toLocaleString() : ''}</td>
                  <td className="px-4 py-2">{item.issues?.length ?? 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
