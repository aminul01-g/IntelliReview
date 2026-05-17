import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { api } from '@/lib/api';
import * as LucideAll from 'lucide-react';
import { FileText, Clock, RefreshCw, AlertCircle, Search } from 'lucide-react';

// Icons extracted via wildcard to handle lucide-react v0.562 bundler resolution
const Folder       = (LucideAll as any).Folder       as React.FC<{ className?: string }>;
const FolderOpen   = (LucideAll as any).FolderOpen   as React.FC<{ className?: string }>;
const Calendar     = (LucideAll as any).Calendar     as React.FC<{ className?: string }>;
const Trash2       = (LucideAll as any).Trash2       as React.FC<{ className?: string }>;
const UploadCloud  = (LucideAll as any).UploadCloud  as React.FC<{ className?: string }>;
const ChevronRight = (LucideAll as any).ChevronRight as React.FC<{ className?: string }>;

interface Project {
  id: number;
  name: string;
  plan_md: string;
  created_at: string;
}

function formatDate(iso: string) {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

export function ProjectList() {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null);

  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ['projects'],
    queryFn: async () => {
      const res = await api.get('/analysis/projects?limit=50');
      return res.data as Project[];
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (projectId: number) => {
      await api.delete(`/analysis/projects/${projectId}`);
    },
    onSuccess: () => {
      setDeleteConfirmId(null);
      refetch();
    },
    onError: () => {
      setDeleteConfirmId(null);
    },
  });

  const projects = (data || []).filter((p: Project) =>
    search.trim() === '' ? true : p.name.toLowerCase().includes(search.toLowerCase())
  );

  // ── Loading skeleton ───────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="space-y-6 animate-in fade-in duration-500">
        <div>
          <div className="h-9 w-48 bg-muted rounded-lg animate-pulse mb-2" />
          <div className="h-5 w-72 bg-muted/60 rounded animate-pulse" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="bg-card border border-border rounded-xl p-5 animate-pulse space-y-3">
              <div className="flex items-center justify-between">
                <div className="h-10 w-10 bg-muted rounded-lg" />
                <div className="h-4 w-16 bg-muted rounded" />
              </div>
              <div className="h-5 w-3/4 bg-muted rounded" />
              <div className="h-4 w-full bg-muted/60 rounded" />
              <div className="h-8 w-full bg-muted rounded-md mt-4" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  // ── Error state ────────────────────────────────────────────────────
  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-4">
        <div className="h-16 w-16 rounded-full bg-destructive/10 flex items-center justify-center">
          <AlertCircle className="h-8 w-8 text-destructive" />
        </div>
        <div className="text-center">
          <p className="text-lg font-semibold text-foreground">Failed to load projects</p>
          <p className="text-sm text-muted-foreground mt-1">There was a problem reaching the server.</p>
        </div>
        <button
          onClick={() => refetch()}
          className="flex items-center gap-2 bg-primary text-primary-foreground h-10 px-5 rounded-md text-sm font-medium hover:bg-primary/90 transition-colors shadow-sm"
        >
          <RefreshCw className="h-4 w-4" /> Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* ── Header ── */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <FolderOpen className="h-8 w-8 text-primary" />
            My Projects
          </h1>
          <p className="text-muted-foreground text-base mt-1">
            {(data || []).length} project{(data || []).length !== 1 ? 's' : ''} analysed &mdash; click any card to explore results.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            title="Refresh"
            className="p-2 rounded-md border border-border hover:bg-muted transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 text-muted-foreground ${isFetching ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={() => navigate('/upload')}
            className="flex items-center gap-2 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-5 rounded-md text-sm font-medium transition-all shadow-sm"
          >
            <UploadCloud className="h-4 w-4" />
            New Upload
          </button>
        </div>
      </div>

      {/* ── Search bar ── */}
      {(data || []).length > 0 && (
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
          <input
            type="text"
            placeholder="Search projects…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 h-10 bg-muted/30 border border-border rounded-lg text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
          />
        </div>
      )}

      {/* ── Project Cards Grid ── */}
      {projects.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((project: Project) => (
            <div
              key={project.id}
              className="group bg-card border border-border rounded-xl p-5 shadow-sm hover:shadow-md hover:border-primary/40 transition-all duration-200 flex flex-col"
            >
              {/* Card header */}
              <div className="flex items-start justify-between mb-3">
                <div className="p-2.5 bg-primary/10 rounded-lg group-hover:bg-primary/20 transition-colors">
                  <Folder className="h-5 w-5 text-primary" />
                </div>
                <span className="text-[11px] text-muted-foreground font-mono flex items-center gap-1 mt-0.5">
                  <Clock className="h-3 w-3" />
                  {timeAgo(project.created_at)}
                </span>
              </div>

              {/* Project name */}
              <h3 className="font-bold text-foreground group-hover:text-primary transition-colors truncate text-base mb-1">
                {project.name}
              </h3>

              {/* Plan preview */}
              <p className="text-xs text-muted-foreground line-clamp-2 italic flex-1 mb-4 min-h-[2.5rem]">
                {project.plan_md?.trim() || 'No analysis plan specified.'}
              </p>

              {/* Date row */}
              <div className="flex items-center gap-1 text-[11px] text-muted-foreground mb-4">
                <Calendar className="h-3 w-3" />
                <span>Created {formatDate(project.created_at)}</span>
              </div>

              {/* Action buttons */}
              <div className="flex items-center gap-2 pt-3 border-t border-border/50">
                <button
                  onClick={() => navigate(`/history?project_id=${project.id}`)}
                  className="flex-1 flex items-center justify-center gap-1.5 bg-secondary text-secondary-foreground hover:bg-secondary/80 h-8 px-3 rounded-md text-xs font-medium transition-colors"
                >
                  <FileText className="h-3 w-3" />
                  View History
                  <ChevronRight className="h-3 w-3 ml-auto opacity-50" />
                </button>

                {deleteConfirmId === project.id ? (
                  <div className="flex gap-1">
                    <button
                      onClick={() => deleteMutation.mutate(project.id)}
                      disabled={deleteMutation.isPending}
                      className="h-8 px-2.5 rounded-md text-xs font-medium bg-destructive text-destructive-foreground hover:bg-destructive/90 transition-colors disabled:opacity-50"
                    >
                      {deleteMutation.isPending ? <RefreshCw className="h-3 w-3 animate-spin" /> : 'Yes'}
                    </button>
                    <button
                      onClick={() => setDeleteConfirmId(null)}
                      className="h-8 px-2.5 rounded-md text-xs font-medium border border-border hover:bg-muted transition-colors"
                    >
                      No
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => setDeleteConfirmId(project.id)}
                    title="Delete project"
                    className="p-2 rounded-md border border-border hover:bg-destructive/10 hover:border-destructive/40 hover:text-destructive transition-colors group/del"
                  >
                    <Trash2 className="h-3.5 w-3.5 text-muted-foreground group-hover/del:text-destructive transition-colors" />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (data || []).length > 0 && search ? (
        /* No search results */
        <div className="text-center py-16 bg-muted/20 rounded-2xl border border-dashed border-border">
          <Search className="h-10 w-10 text-muted-foreground/40 mx-auto mb-3" />
          <p className="text-foreground font-medium">No projects match &ldquo;{search}&rdquo;</p>
          <p className="text-sm text-muted-foreground mt-1">Try a different search term.</p>
        </div>
      ) : (
        /* Truly empty state */
        <div className="text-center py-24 bg-muted/10 rounded-2xl border-2 border-dashed border-border">
          <div className="flex justify-center mb-5">
            <div className="h-20 w-20 rounded-full bg-primary/10 flex items-center justify-center">
              <Folder className="h-10 w-10 text-primary/60" />
            </div>
          </div>
          <h3 className="text-xl font-semibold text-foreground">No projects yet</h3>
          <p className="text-sm text-muted-foreground mt-2 mb-7 max-w-sm mx-auto">
            Upload a repository or set of source files to run a comprehensive multi-agent scan.
          </p>
          <button
            onClick={() => navigate('/upload')}
            className="inline-flex items-center gap-2 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-7 rounded-md font-medium text-sm transition-all shadow-md"
          >
            <UploadCloud className="h-4 w-4" />
            Upload Your First Project
          </button>
        </div>
      )}
    </div>
  );
}
