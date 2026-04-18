import React, { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { useMutation, useQuery } from '@tanstack/react-query';


import { useAuth } from '@/contexts/AuthContext';

import type { AuthContextType } from '@/contexts/AuthContext';

export function AdminPolicyManager() {
  const { user } = useAuth() as AuthContextType;
  const [policies, setPolicies] = useState([]);
  const [editing, setEditing] = useState(false);
  const [editValue, setEditValue] = useState('');

  // Fetch global policies
  const { data, refetch, isLoading, isError } = useQuery({
    queryKey: ['globalPolicies'],
    queryFn: async () => {
      const { data } = await api.get('/global');
      return data;
    },
    enabled: !!user && user.role === 'Admin',
  });

  useEffect(() => {
    if (data && data.rules) {
      setPolicies(data.rules);
      setEditValue(JSON.stringify(data.rules, null, 2));
    }
  }, [data]);

  // Update global policies
  const updateMutation = useMutation({
    mutationFn: async (rules: any) => {
      const { data } = await api.put('/global', { rules });
      return data;
    },
    onSuccess: () => {
      setEditing(false);
      refetch();
    },
  });

  if (!user || user.role !== 'Admin') {
    return <div className="p-8 text-center text-muted-foreground">Admin access required to manage global policies.</div>;
  }

  // Local Card component (copied from ProfileSettings)
  const Card = ({ title, children }: { title: string, children: React.ReactNode }) => (
    <div className="bg-slate-950 rounded-2xl border border-slate-800 p-6 md:p-8 shadow-xl backdrop-blur-sm relative overflow-hidden">
      <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-600 to-indigo-600 opacity-50"></div>
      <h2 className="text-xl font-bold text-white mb-6 tracking-tight">{title}</h2>
      {children}
    </div>
  );

  return (
    <div className="max-w-3xl mx-auto py-10 space-y-6">
      <h1 className="text-2xl font-bold mb-2">Organization Policy Management</h1>
      <p className="text-muted-foreground mb-6">View and edit global policy rules enforced across all repositories. Only admins can update these policies.</p>
      <Card title="Global Policy Rules">
        {isLoading ? (
          <div>Loading policies...</div>
        ) : isError ? (
          <div className="text-destructive">Failed to load policies.</div>
        ) : (
          <>
            {!editing ? (
              <>
                <pre className="bg-muted/40 border border-border rounded-md p-4 text-xs overflow-x-auto mb-4">
                  {JSON.stringify(policies, null, 2)}
                </pre>
                <button
                  onClick={() => setEditing(true)}
                  className="bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2 rounded-md font-medium text-sm transition-colors disabled:opacity-50 shadow-sm"
                >
                  Edit Policies
                </button>
              </>
            ) : (
              <>
                <textarea
                  className="w-full h-64 border border-border rounded-md p-2 font-mono text-xs mb-4"
                  value={editValue}
                  onChange={e => setEditValue(e.target.value)}
                />
                <div className="flex gap-2">
                  <button
                    onClick={() => {
                      try {
                        const parsed = JSON.parse(editValue);
                        updateMutation.mutate(parsed);
                      } catch (e) {
                        alert('Invalid JSON');
                      }
                    }}
                    className="bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2 rounded-md font-medium text-sm transition-colors disabled:opacity-50 shadow-sm"
                    disabled={updateMutation.isPending}
                  >
                    Save
                  </button>
                  <button
                    onClick={() => setEditing(false)}
                    className="bg-muted text-foreground border border-border h-10 px-4 py-2 rounded-md font-medium text-sm transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </>
            )}
          </>
        )}
      </Card>
    </div>
  );
}
