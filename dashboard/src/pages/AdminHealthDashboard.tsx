import React, { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';

export function AdminHealthDashboard() {
  const { user } = useAuth();
  const [health, setHealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [aggResult, setAggResult] = useState<any>(null);
  const [aggLoading, setAggLoading] = useState(false);

  useEffect(() => {
    async function fetchHealth() {
      setLoading(true);
      setError('');
      try {
        const { data } = await api.get('/health');
        setHealth(data);
      } catch (e: any) {
        setError(e.response?.data?.detail || e.message || 'Failed to fetch health status');
      } finally {
        setLoading(false);
      }
    }
    fetchHealth();
  }, []);

  const triggerAggregation = async () => {
    setAggLoading(true);
    setAggResult(null);
    try {
      const { data } = await api.post('/trigger-aggregation');
      setAggResult(data);
    } catch (e: any) {
      setAggResult({ error: e.response?.data?.detail || e.message || 'Failed to trigger aggregation' });
    } finally {
      setAggLoading(false);
    }
  };

  if (!user || user.role !== 'Admin') {
    return <div className="p-8 text-center text-muted-foreground">Admin access required to view system health.</div>;
  }

  return (
    <div className="max-w-2xl mx-auto py-10 space-y-6">
      <h1 className="text-2xl font-bold mb-2">System Health & Operations</h1>
      <p className="text-muted-foreground mb-6">Monitor the status of backend services and trigger maintenance operations.</p>
      <div className="bg-slate-950 rounded-2xl border border-slate-800 p-6 shadow-xl">
        <h2 className="text-lg font-semibold mb-4">Analysis History Service</h2>
        {loading ? (
          <div>Loading health status...</div>
        ) : error ? (
          <div className="text-destructive">{error}</div>
        ) : (
          <pre className="bg-muted/40 border border-border rounded-md p-4 text-xs overflow-x-auto mb-4">
            {JSON.stringify(health, null, 2)}
          </pre>
        )}
        <button
          onClick={triggerAggregation}
          className="bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2 rounded-md font-medium text-sm transition-colors disabled:opacity-50 shadow-sm"
          disabled={aggLoading}
        >
          {aggLoading ? 'Triggering...' : 'Trigger Aggregation'}
        </button>
        {aggResult && (
          <pre className="bg-muted/40 border border-border rounded-md p-4 text-xs overflow-x-auto mt-4">
            {JSON.stringify(aggResult, null, 2)}
          </pre>
        )}
      </div>
    </div>
  );
}
