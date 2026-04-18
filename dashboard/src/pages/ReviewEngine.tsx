import React, { useState } from 'react'
import * as Lucide from 'lucide-react'

const { FileCode, Play, AlertCircle, CheckCircle, ShieldAlert, Check, X } = Lucide as any
import { useSubmitAnalysis, useAnalysisTaskStatus } from '@/hooks/useAnalysisTask'
import { useTelemetryFeedback } from '@/hooks/useTelemetryFeedback'
import { useReviewFeedback } from '@/hooks/useReviewFeedback'


const SuggestionCard = ({ suggestion, taskId }: { suggestion: any, taskId?: string }) => {
  const [resolved, setResolved] = useState<boolean>(false);
  const telemetry = useTelemetryFeedback();
  const { requestBetterFix, ignorePattern } = useReviewFeedback();
  const [feedbackMsg, setFeedbackMsg] = useState<string | null>(null);

  const handleAction = (action: 'accept' | 'reject') => {
    telemetry.mutate({
      rule_id: suggestion.rule_id || 'UNKNOWN_RULE',
      action,
      task_id: taskId,
      line_number: suggestion.line
    }, {
      onSuccess: () => setResolved(true)
    });
  };

  const handleRequestBetterFix = async () => {
    setFeedbackMsg(null);
    try {
      await requestBetterFix.mutateAsync({
        finding_id: suggestion.rule_id || suggestion.id || 'UNKNOWN',
        action: 'request_better_fix',
        comment: '',
        repository: 'unknown',
        pr_number: 0
      });
      setFeedbackMsg('Requested a better fix. Thank you!');
    } catch (e) {
      setFeedbackMsg('Failed to request better fix.');
    }
  };

  const handleIgnorePattern = async () => {
    setFeedbackMsg(null);
    try {
      await ignorePattern.mutateAsync({
        finding_id: suggestion.rule_id || suggestion.id || 'UNKNOWN',
        action: 'ignore_pattern',
        comment: '',
        repository: 'unknown',
        pr_number: 0
      });
      setFeedbackMsg('Pattern will be ignored in future reviews.');
    } catch (e) {
      setFeedbackMsg('Failed to ignore pattern.');
    }
  };

  if (resolved) {
    return (
      <div className="border border-border/50 rounded-md p-3 opacity-50 text-sm flex items-center justify-between bg-muted/20">
        <span className="line-through text-muted-foreground">{suggestion.title || 'Security Issue Resolved'}</span>
        <span className="text-xs text-muted-foreground max-w-[150px] truncate">Telemetry Feedback Sent</span>
      </div>
    );
  }

  return (
    <div className="border border-destructive/20 bg-destructive/5 flex flex-col gap-3 rounded-md p-3 text-sm transition-opacity">
      <div className="flex items-start gap-2">
         <ShieldAlert className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
         <div className="flex-1">
            <div className="font-semibold text-foreground flex items-center justify-between">
              {suggestion.title || 'Security Vulnerability Detected'}
              <span className="px-2 py-0.5 rounded-full bg-destructive/10 text-destructive text-[10px] font-mono border border-destructive/20 tracking-wider">
                {suggestion.rule_id || 'CWE-89'}
              </span>
            </div>
            <p className="text-muted-foreground mt-1 line-clamp-2 leading-relaxed">{suggestion.description}</p>
         </div>
      </div>
      
      {suggestion.fix && (
        <div className="bg-background/80 border border-border rounded p-2.5 text-xs font-mono text-muted-foreground overflow-x-auto">
          {suggestion.fix}
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2 mt-1 border-t border-destructive/10 pt-3">
        <button
          onClick={() => handleAction('accept')}
          disabled={telemetry.isPending}
          className="bg-green-500/10 hover:bg-green-500/20 text-green-500 border border-green-500/20 px-3 py-1.5 rounded-md text-xs font-medium flex items-center gap-1.5 transition-colors"
        >
          <Check className="h-3.5 w-3.5" /> Accept Fix
        </button>
        <button
          onClick={() => handleAction('reject')}
          disabled={telemetry.isPending}
          className="bg-transparent hover:bg-muted/50 text-muted-foreground border border-border px-3 py-1.5 rounded-md text-xs font-medium flex items-center gap-1.5 transition-colors"
        >
          <X className="h-3.5 w-3.5" /> Reject (False Positive)
        </button>
        <button
          onClick={handleRequestBetterFix}
          disabled={requestBetterFix.isPending}
          className="bg-blue-500/10 hover:bg-blue-500/20 text-blue-500 border border-blue-500/20 px-3 py-1.5 rounded-md text-xs font-medium flex items-center gap-1.5 transition-colors"
        >
          <Lucide.Wand2 className="h-3.5 w-3.5" /> Request Better Fix
        </button>
        <button
          onClick={handleIgnorePattern}
          disabled={ignorePattern.isPending}
          className="bg-yellow-500/10 hover:bg-yellow-500/20 text-yellow-500 border border-yellow-500/20 px-3 py-1.5 rounded-md text-xs font-medium flex items-center gap-1.5 transition-colors"
        >
          <Lucide.EyeOff className="h-3.5 w-3.5" /> Ignore Pattern
        </button>
        {feedbackMsg && <span className="text-xs text-muted-foreground ml-2">{feedbackMsg}</span>}
      </div>
    </div>
  )
}

export function ReviewEngine() {
  const [diffInput, setDiffInput] = useState('');
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);

  const submitMutation = useSubmitAnalysis();
  const { data: taskData, isLoading: isPolling } = useAnalysisTaskStatus(activeTaskId);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!diffInput.trim()) return;
    // Only send the diff, as expected by backend
    submitMutation.mutate({ diff: diffInput }, {
      onSuccess: (data: any) => {
        setActiveTaskId(data.task_id);
      }
    });
  }

  const isAnalyzing = (isPolling && activeTaskId) || taskData?.status === 'processing' || taskData?.status === 'pending';
  const isCompleted = taskData?.status === 'completed';
  const isFailed = taskData?.status === 'failed';

  // Only use real issues from backend
  const issues = taskData?.result?.issues || [];

  return (
    <div className="space-y-6 flex flex-col h-[calc(100vh-8rem)]">
      <div className="flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Review Engine</h1>
          <p className="text-muted-foreground">Interactive AI diff review and telemetry feedback.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 flex-1 min-h-0">
        {/* Left pane: Input */}
        <div className="flex flex-col gap-4 border border-border rounded-lg bg-card p-4 min-h-0">
          <div className="flex items-center gap-2 text-sm font-medium border-b border-border pb-2 shrink-0">
            <FileCode className="h-4 w-4" /> Git Diff Input
          </div>
          <form onSubmit={handleSubmit} className="flex-1 flex flex-col gap-4 min-h-0">
            <textarea
              className="flex-1 bg-background border border-input rounded-md p-3 text-sm font-mono text-foreground focus:outline-none focus:ring-1 focus:ring-ring resize-none leading-relaxed"
              placeholder="Paste your git diff or code snippet here..."
              value={diffInput}
              onChange={(e) => setDiffInput(e.target.value)}
              disabled={isAnalyzing || submitMutation.isPending}
            />
            <button 
              type="submit"
              disabled={isAnalyzing || submitMutation.isPending || !diffInput.trim()}
              className="shrink-0 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2 rounded-md font-medium text-sm flex items-center justify-center gap-2 transition-colors disabled:opacity-50 shadow-sm"
            >
              {isAnalyzing || submitMutation.isPending ? (
                <div className="h-4 w-4 rounded-full border-2 border-primary-foreground border-t-transparent animate-spin" />
              ) : (
                <Play className="h-4 w-4 fill-current" />
              )}
              {isAnalyzing ? 'Analyzing with Multi-Agent Pipeline...' : 'Run Security Analysis'}
            </button>
          </form>
        </div>

        {/* Right pane: Output/Status */}
        <div className="flex flex-col gap-4 border border-border rounded-lg bg-card p-4 relative min-h-0 shadow-sm">
           <div className="flex items-center gap-2 text-sm font-medium border-b border-border pb-2 shrink-0">
              Results & Telemetry
              {isAnalyzing && <span className="ml-auto text-xs font-semibold text-primary animate-pulse tracking-wide">AI processing task {activeTaskId?.slice(0,6)}...</span>}
           </div>

           {!activeTaskId ? (
             <div className="flex-1 flex items-center justify-center text-muted-foreground text-sm flex-col gap-3">
               <div className="h-12 w-12 rounded-full bg-muted/50 flex items-center justify-center mb-2">
                 <FileCode className="h-6 w-6 opacity-40" />
               </div>
               Waiting for diff input...
             </div>
           ) : isAnalyzing ? (
             <div className="flex-1 flex flex-col gap-5 pt-4">
               {/* Skeleton Loaders */}
                <div className="space-y-3">
                  <div className="h-5 w-3/4 bg-muted rounded animate-pulse"></div>
                  <div className="h-4 w-1/2 bg-muted/60 rounded animate-pulse"></div>
                </div>
                <div className="space-y-2 mt-4">
                  <div className="h-32 w-full bg-muted/40 rounded border border-border/50 animate-pulse"></div>
                  <div className="flex gap-2 pt-2">
                     <div className="h-8 w-24 bg-muted/60 rounded animate-pulse"></div>
                     <div className="h-8 w-24 bg-muted/60 rounded animate-pulse"></div>
                  </div>
                </div>
             </div>
           ) : isFailed ? (
             <div className="flex-1 flex items-center justify-center text-destructive flex-col gap-2">
                <AlertCircle className="h-10 w-10 mb-2 opacity-80" />
                <span className="font-semibold text-lg tracking-tight">Analysis Task Failed</span>
                <span className="text-sm opacity-80">The Celery backend worker encountered an error.</span>
             </div>
           ) : isCompleted ? (
             <div className="flex-1 flex flex-col gap-4 overflow-hidden">
               <div className="bg-green-500/10 text-green-500 border border-green-500/20 rounded-md p-3 text-sm flex items-start gap-2 shrink-0">
                 <CheckCircle className="h-5 w-5 shrink-0 mt-0.5" />
                 <div>
                   <p className="font-semibold">Analysis Complete</p>
                   <p className="opacity-90 mt-0.5 text-xs">Awaiting your feedback on these suggestions to refine our False Positive Rates.</p>
                 </div>
               </div>
               
               <div className="flex-1 overflow-auto space-y-4 pr-1 custom-scrollbar">
                 {issues.length === 0 ? (
                   <div className="text-muted-foreground text-sm text-center py-8">No issues found in this analysis.</div>
                 ) : (
                   issues.map((issue: any, index: number) => (
                     <SuggestionCard key={index} suggestion={issue} taskId={activeTaskId} />
                   ))
                 )}
               </div>
             </div>
           ) : null}
        </div>
      </div>
    </div>
  )
}
