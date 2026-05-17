import React, { useEffect, useState } from 'react';
import * as Lucide from 'lucide-react';
import { api } from '@/lib/api';

const { Activity } = Lucide as any;

interface QueueStatus {
  status: string;
  queues: {
    bulk: number;
    express: number;
    default: number;
  };
  total_pending: number;
  health: 'green' | 'yellow' | 'red';
}

export const QueueStatusIndicator = () => {
  const [status, setStatus] = useState<QueueStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchStatus = async () => {
    try {
      const response = await api.get('/queue_status/status');
      setStatus(response.data);
    } catch (err) {
      console.error('Failed to fetch queue status:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 30000); // Poll every 30s
    return () => clearInterval(interval);
  }, []);

  if (isLoading || !status) {
    return (
      <div className="flex items-center gap-2 px-2 py-1 text-xs text-muted-foreground opacity-60">
        <div className="h-2 w-2 rounded-full bg-muted-foreground animate-pulse" />
        Checking system load...
      </div>
    );
  }

  const healthColor = {
    green: 'text-emerald-500 bg-emerald-500/10 border-emerald-500/20',
    yellow: 'text-amber-500 bg-amber-500/10 border-amber-500/20',
    red: 'text-destructive bg-destructive/10 border-destructive/20',
  }[status.health as 'green' | 'yellow' | 'red'] || 'text-muted-foreground';

  return (
    <div className={`flex items-center gap-2 px-2 py-1 rounded-full border text-xs font-medium transition-colors ${healthColor}`}>
      <Activity className="h-3 w-3" />
      <span>Queue: {status.total_pending} pending</span>
    </div>
  );
};
