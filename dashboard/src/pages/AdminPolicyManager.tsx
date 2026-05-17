import React, { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useAuth } from '@/contexts/AuthContext';
import type { AuthContextType } from '@/contexts/AuthContext';
// @ts-ignore – lucide-react v0.562 barrel exports resolve correctly at Vite runtime
import { Shield, Users, Globe, Save, Lock, ChevronDown, ChevronUp, Info, X, RefreshCw, CheckCircle, AlertCircle, Pencil } from 'lucide-react';

// ── Shared sub-components ──────────────────────────────────────────────────

function PolicyCard({
  icon: Icon,
  iconColor,
  title,
  subtitle,
  children,
}: {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  icon: React.FC<{ className?: string }>;
  iconColor: string;
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-card border border-border rounded-2xl shadow-sm overflow-hidden">
      {/* Coloured top bar */}
      <div className={`h-1 w-full ${iconColor}`} />
      <div className="p-6 md:p-8">
        <div className="flex items-center gap-3 mb-1">
          <div className={`p-2 rounded-lg bg-opacity-15 ${iconColor.replace('bg-', 'bg-').replace('-600', '/15')}`}>
            <Icon className={`h-5 w-5 ${iconColor.replace('bg-', 'text-')}`} />
          </div>
          <div>
            <h2 className="text-lg font-bold text-foreground tracking-tight">{title}</h2>
            <p className="text-xs text-muted-foreground">{subtitle}</p>
          </div>
        </div>
        <div className="mt-6">{children}</div>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: 'idle' | 'success' | 'error' }) {
  if (status === 'idle') return null;
  return (
    <div
      className={`flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-full ${
        status === 'success'
          ? 'bg-green-500/10 text-green-500'
          : 'bg-destructive/10 text-destructive'
      }`}
    >
      {status === 'success' ? (
        <><CheckCircle className="h-3.5 w-3.5" /> Saved successfully</>
      ) : (
        <><AlertCircle className="h-3.5 w-3.5" /> Save failed</>
      )}
    </div>
  );
}

function JsonEditor({
  value,
  onChange,
  readOnly,
}: {
  value: string;
  onChange: (v: string) => void;
  readOnly?: boolean;
}) {
  return (
    <textarea
      readOnly={readOnly}
      className={`w-full h-56 border border-border rounded-lg p-3 font-mono text-xs resize-none leading-relaxed transition-colors focus:outline-none focus:ring-2 focus:ring-primary/40 ${
        readOnly
          ? 'bg-muted/30 text-muted-foreground cursor-default'
          : 'bg-background text-foreground'
      }`}
      value={value}
      onChange={(e) => onChange(e.target.value)}
    />
  );
}

// ── SECTION 1: Global Rules Reference ─────────────────────────────────────

function GlobalRulesSection() {
  const [open, setOpen] = useState(true);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['globalRulesCatalog'],
    queryFn: async () => {
      const { data } = await api.get('/policies/global/rules');
      return data as Record<string, string[]>;
    },
  });

  return (
    <PolicyCard
      icon={Globe}
      iconColor="bg-blue-600"
      title="Global Rule Catalog"
      subtitle="System-wide rules available across all repositories"
    >
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors mb-4"
      >
        {open ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        {open ? 'Collapse' : 'Expand'} rule catalog
      </button>

      {open && (
        <>
          {isLoading ? (
            <div className="animate-pulse space-y-2">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-10 bg-muted rounded-md" />
              ))}
            </div>
          ) : isError ? (
            <p className="text-sm text-destructive flex items-center gap-1.5">
              <AlertCircle className="h-4 w-4" /> Failed to load rule catalog.
            </p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {data &&
                Object.entries(data).map(([category, rules]) => (
                  <div key={category} className="bg-muted/30 rounded-lg p-3 border border-border/50">
                    <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-2">
                      {category}
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {(rules as string[]).map((rule: string) => (
                        <span
                          key={rule}
                          className="text-[11px] font-mono bg-background border border-border px-2 py-0.5 rounded text-foreground/80"
                        >
                          {rule}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
            </div>
          )}
        </>
      )}
    </PolicyCard>
  );
}

// ── SECTION 2: Team Policy Manager ────────────────────────────────────────

function TeamPolicySection({ isAdmin }: { isAdmin: boolean }) {
  const [editing, setEditing] = useState(false);
  const [editValue, setEditValue] = useState('');
  const [saveStatus, setSaveStatus] = useState<'idle' | 'success' | 'error'>('idle');

  const { data, refetch, isLoading, isError } = useQuery({
    queryKey: ['teamPolicy'],
    queryFn: async () => {
      const { data } = await api.get('/policies/team/policy');
      return data;
    },
  });

  useEffect(() => {
    if (data?.custom_rules !== undefined) {
      setEditValue(JSON.stringify(data.custom_rules, null, 2));
    }
  }, [data]);

  const updateMutation = useMutation({
    mutationFn: async (rules: Record<string, unknown>) => {
      const { data } = await api.post('/policies/team/policy/update', { custom_rules: rules });
      return data;
    },
    onSuccess: () => {
      setSaveStatus('success');
      setEditing(false);
      refetch();
      setTimeout(() => setSaveStatus('idle'), 4000);
    },
    onError: () => {
      setSaveStatus('error');
      setTimeout(() => setSaveStatus('idle'), 4000);
    },
  });

  const handleSave = () => {
    try {
      const parsed = JSON.parse(editValue) as Record<string, unknown>;
      updateMutation.mutate(parsed);
    } catch {
      alert('Invalid JSON — please fix the syntax before saving.');
    }
  };

  return (
    <PolicyCard
      icon={Users}
      iconColor="bg-indigo-500"
      title="Team Policy Overrides"
      subtitle={
        data?.team_name
          ? `Custom rules for team: ${data.team_name}`
          : 'Team-specific severity and rule overrides'
      }
    >
      {/* No-team notice */}
      {!isLoading && !isError && data?.message && (
        <div className="flex items-start gap-2 text-sm text-muted-foreground bg-muted/30 border border-border rounded-lg p-3 mb-4">
          <Info className="h-4 w-4 mt-0.5 shrink-0 text-blue-400" />
          <span>{data.message} Global defaults are applied.</span>
        </div>
      )}

      {/* Read-only notice for non-admins */}
      {!isAdmin && (
        <div className="flex items-start gap-2 text-sm text-amber-500 bg-amber-500/10 border border-amber-500/20 rounded-lg p-3 mb-4">
          <Lock className="h-4 w-4 mt-0.5 shrink-0" />
          <span>You have read-only access to team policies. Contact an admin to request changes.</span>
        </div>
      )}

      {isLoading ? (
        <div className="animate-pulse h-40 bg-muted rounded-lg" />
      ) : isError ? (
        <p className="text-sm text-destructive flex items-center gap-1.5">
          <AlertCircle className="h-4 w-4" /> Failed to load team policy.
        </p>
      ) : (
        <div className="space-y-4">
          {/* Team metadata */}
          {data?.team_name && (
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Base policy:</span>
              <span className="font-mono text-xs bg-muted px-2 py-1 rounded text-foreground">
                {data.global_defaults}
              </span>
            </div>
          )}

          {/* JSON editor / viewer */}
          {editing ? (
            <>
              <div className="text-xs text-muted-foreground bg-muted/30 border border-border rounded-md px-3 py-2 flex items-center gap-1.5">
                <Info className="h-3.5 w-3.5" />
                Map rule IDs to severity overrides, e.g.{' '}
                <code className="font-mono bg-muted px-1 rounded">{'{"sql_injection":"critical"}'}</code>
              </div>
              <JsonEditor value={editValue} onChange={setEditValue} />
              <div className="flex items-center justify-between gap-3">
                <StatusBadge status={saveStatus} />
                <div className="flex gap-2 ml-auto">
                  <button
                    onClick={() => { setEditing(false); setSaveStatus('idle'); }}
                    className="flex items-center gap-1.5 h-9 px-4 rounded-md text-sm font-medium border border-border hover:bg-muted transition-colors"
                  >
                    <X className="h-4 w-4" /> Cancel
                  </button>
                  <button
                    onClick={handleSave}
                    disabled={updateMutation.isPending}
                    className="flex items-center gap-1.5 h-9 px-5 rounded-md text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 shadow-sm"
                  >
                    {updateMutation.isPending ? (
                      <RefreshCw className="h-4 w-4 animate-spin" />
                    ) : (
                      <Save className="h-4 w-4" />
                    )}
                    Save Policy
                  </button>
                </div>
              </div>
            </>
          ) : (
            <>
              <JsonEditor
                value={JSON.stringify(data?.custom_rules ?? {}, null, 2)}
                onChange={() => {}}
                readOnly
              />
              <div className="flex items-center justify-between">
                <StatusBadge status={saveStatus} />
                {isAdmin && (
                  <button
                    onClick={() => setEditing(true)}
                    className="flex items-center gap-1.5 h-9 px-4 rounded-md text-sm font-medium border border-border hover:bg-muted transition-colors ml-auto"
                  >
                    <Pencil className="h-4 w-4" /> Edit Policy
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      )}
    </PolicyCard>
  );
}

// ── SECTION 3: Global Policy Editor (Admin-only) ───────────────────────────

function GlobalPolicyEditorSection() {
  const [editing, setEditing] = useState(false);
  const [editValue, setEditValue] = useState('');
  const [saveStatus, setSaveStatus] = useState<'idle' | 'success' | 'error'>('idle');

  const { data, refetch, isLoading, isError } = useQuery({
    queryKey: ['globalPolicies'],
    queryFn: async () => {
      const { data } = await api.get('/policies/global/rules');
      return data;
    },
  });

  useEffect(() => {
    if (data) {
      setEditValue(JSON.stringify(data, null, 2));
    }
  }, [data]);

  const updateMutation = useMutation({
    mutationFn: async (rules: Record<string, unknown>) => {
      const { data } = await api.post('/policies/team/policy/update', { custom_rules: rules });
      return data;
    },
    onSuccess: () => {
      setSaveStatus('success');
      setEditing(false);
      refetch();
      setTimeout(() => setSaveStatus('idle'), 4000);
    },
    onError: () => {
      setSaveStatus('error');
      setTimeout(() => setSaveStatus('idle'), 4000);
    },
  });

  const handleSave = () => {
    try {
      const parsed = JSON.parse(editValue);
      updateMutation.mutate(parsed);
    } catch {
      alert('Invalid JSON — please fix the syntax before saving.');
    }
  };

  return (
    <PolicyCard
      icon={Shield}
      iconColor="bg-violet-600"
      title="Global Policy Editor"
      subtitle="Organisation-wide defaults applied to all teams"
    >
      <div className="flex items-start gap-2 text-xs text-amber-500 bg-amber-500/10 border border-amber-500/20 rounded-lg p-3 mb-4">
        <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
        Changes here affect every team in the organisation. Proceed with care.
      </div>

      {isLoading ? (
        <div className="animate-pulse h-40 bg-muted rounded-lg" />
      ) : isError ? (
        <p className="text-sm text-destructive flex items-center gap-1.5">
          <AlertCircle className="h-4 w-4" /> Failed to load global policies.
        </p>
      ) : editing ? (
        <div className="space-y-4">
          <JsonEditor value={editValue} onChange={setEditValue} />
          <div className="flex items-center justify-between gap-3">
            <StatusBadge status={saveStatus} />
            <div className="flex gap-2 ml-auto">
              <button
                onClick={() => { setEditing(false); setSaveStatus('idle'); }}
                className="flex items-center gap-1.5 h-9 px-4 rounded-md text-sm font-medium border border-border hover:bg-muted transition-colors"
              >
                <X className="h-4 w-4" /> Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={updateMutation.isPending}
                className="flex items-center gap-1.5 h-9 px-5 rounded-md text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 shadow-sm"
              >
                {updateMutation.isPending ? (
                  <RefreshCw className="h-4 w-4 animate-spin" />
                ) : (
                  <Save className="h-4 w-4" />
                )}
                Apply Globally
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <JsonEditor
            value={JSON.stringify(data, null, 2)}
            onChange={() => {}}
            readOnly
          />
          <div className="flex items-center justify-between">
            <StatusBadge status={saveStatus} />
            <button
              onClick={() => setEditing(true)}
              className="flex items-center gap-1.5 h-9 px-4 rounded-md text-sm font-medium border border-border hover:bg-muted transition-colors ml-auto"
            >
              <Pencil className="h-4 w-4" /> Edit Global Policy
            </button>
          </div>
        </div>
      )}
    </PolicyCard>
  );
}

// ── Page root ──────────────────────────────────────────────────────────────

export function AdminPolicyManager() {
  const { user } = useAuth() as AuthContextType;

  const isAdmin = !!user && user.role === 'Admin';
  const isReviewer = !!user && user.role === 'Reviewer';
  const hasAccess = isAdmin || isReviewer;

  if (!hasAccess) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-4 text-center">
        <div className="h-16 w-16 rounded-full bg-destructive/10 flex items-center justify-center">
          <Lock className="h-8 w-8 text-destructive" />
        </div>
        <p className="text-lg font-semibold text-foreground">Access Restricted</p>
        <p className="text-sm text-muted-foreground max-w-xs">
          Policy management is only available to users with the <strong>Admin</strong> or <strong>Reviewer</strong> role.
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in duration-500 py-2">
      {/* ── Page header ── */}
      <div className="flex items-start gap-4">
        <div className="p-3 bg-primary/10 rounded-xl hidden sm:flex">
          <Shield className="h-7 w-7 text-primary" />
        </div>
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Policy Management</h1>
          <p className="text-muted-foreground mt-1 text-base">
            Configure global and team-specific review policies that govern how IntelliReview flags and prioritises issues.
          </p>
        </div>
      </div>

      {/* ── Role badge ── */}
      <div className="flex items-center gap-2 text-xs font-medium">
        <span className="text-muted-foreground">Logged in as:</span>
        <span
          className={`px-2.5 py-1 rounded-full font-semibold ${
            isAdmin
              ? 'bg-violet-500/10 text-violet-400 border border-violet-500/20'
              : 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
          }`}
        >
          {user?.role}
        </span>
        {isAdmin && (
          <span className="text-muted-foreground ml-1">— full read/write access to all policy sections</span>
        )}
        {isReviewer && (
          <span className="text-muted-foreground ml-1">— read-only access to team policies</span>
        )}
      </div>

      {/* ── Sections ── */}
      <GlobalRulesSection />
      <TeamPolicySection isAdmin={isAdmin} />
      {isAdmin && <GlobalPolicyEditorSection />}
    </div>
  );
}
