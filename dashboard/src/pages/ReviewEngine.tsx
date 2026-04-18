import React, { useState, useEffect, useRef } from 'react'
import * as Lucide from 'lucide-react'

const { FileCode, Play, AlertCircle, CheckCircle } = Lucide as any
import { useSubmitAnalysis, useAnalysisTaskStatus } from '@/hooks/useAnalysisTask'
import { useTelemetryFeedback } from '@/hooks/useTelemetryFeedback'
import { useReviewFeedback } from '@/hooks/useReviewFeedback'

const SuggestionCard = ({ suggestion, taskId }: { suggestion: any; taskId?: string }) => {
  const [resolved, setResolved] = useState(false)
  const telemetry = useTelemetryFeedback()
  const { requestBetterFix, ignorePattern } = useReviewFeedback()
  const [feedbackMsg, setFeedbackMsg] = useState<string | null>(null)

  const handleAction = (action: 'accept' | 'reject') => {
    telemetry.mutate(
      {
        rule_id: suggestion.rule_id || 'UNKNOWN_RULE',
        action,
        task_id: taskId,
        line_number: suggestion.line
      },
      {
        onSuccess: () => setResolved(true)
      }
    )
  }

  const handleRequestBetterFix = async () => {
    setFeedbackMsg(null)
    try {
      await requestBetterFix.mutateAsync({
        finding_id: suggestion.rule_id || suggestion.id || 'UNKNOWN',
        action: 'request_better_fix',
        comment: '',
        repository: 'unknown',
        pr_number: 0
      })
      setFeedbackMsg('Requested a better fix. Thank you!')
    } catch (e) {
      setFeedbackMsg('Failed to request better fix.')
    }
  }

  const handleIgnorePattern = async () => {
    setFeedbackMsg(null)
    try {
      await ignorePattern.mutateAsync({
        finding_id: suggestion.rule_id || suggestion.id || 'UNKNOWN',
        action: 'ignore_pattern',
        comment: '',
        repository: 'unknown',
        pr_number: 0
      })
      setFeedbackMsg('Pattern will be ignored in future reviews.')
    } catch (e) {
      setFeedbackMsg('Failed to ignore pattern.')
    }
  }

  if (resolved) {
    return (
      <div className="border border-border/50 rounded-md p-3 opacity-50 text-sm flex items-center justify-between bg-muted/20">
        <span className="line-through text-muted-foreground">{suggestion.title || 'Security Issue Resolved'}</span>
        <span className="text-xs text-muted-foreground max-w-[150px] truncate">Telemetry Feedback Sent</span>
      </div>
    )
  }

  return (
    <div className="border border-border/50 rounded-lg p-4 bg-background/80 shadow-sm">
      <div className="flex items-start gap-3 mb-3">
        <div className="rounded-md bg-primary/10 p-2 text-primary">
          <FileCode className="h-5 w-5" />
        </div>
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-foreground">{suggestion.title || 'Security finding'}</h3>
          <p className="text-xs text-muted-foreground mt-1">Rule: {suggestion.rule_id || suggestion.id || 'N/A'}</p>
        </div>
      </div>
      <div className="space-y-3 text-sm text-muted-foreground">
        <p>{suggestion.description || suggestion.message || 'No description available.'}</p>
        <div className="grid grid-cols-2 gap-2">
          <button
            type="button"
            onClick={() => handleAction('accept')}
            className="rounded-md bg-emerald-500/10 text-emerald-500 px-3 py-2 text-xs font-medium hover:bg-emerald-500/15 transition"
          >
            Accept Suggestion
          </button>
          <button
            type="button"
            onClick={() => handleAction('reject')}
            className="rounded-md bg-destructive/10 text-destructive px-3 py-2 text-xs font-medium hover:bg-destructive/15 transition"
          >
            Reject Suggestion
          </button>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={handleRequestBetterFix}
          className="rounded-md border border-border px-3 py-2 text-xs bg-muted hover:bg-muted/80 transition"
        >
          Request Better Fix
        </button>
        <button
          type="button"
          onClick={handleIgnorePattern}
          className="rounded-md border border-border px-3 py-2 text-xs bg-muted hover:bg-muted/80 transition"
        >
          Ignore Pattern
        </button>
      </div>
      {feedbackMsg && <p className="mt-3 text-xs text-muted-foreground">{feedbackMsg}</p>}
    </div>
  )
}

const ReviewEngine = () => {
  const [diffInput, setDiffInput] = useState('')
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null)
  const [timeoutReached, setTimeoutReached] = useState(false)
  const [fallbackDetected, setFallbackDetected] = useState(false)
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const submitMutation = useSubmitAnalysis()
  const { data: taskData, isLoading: isPolling } = useAnalysisTaskStatus(activeTaskId)

  useEffect(() => {
    setTimeoutReached(false)
    setFallbackDetected(false)

    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
    }

    if ((taskData?.status === 'processing' || taskData?.status === 'pending') && activeTaskId) {
      timeoutRef.current = setTimeout(() => {
        setTimeoutReached(true)
      }, 60000)
    }

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
    }
  }, [taskData, activeTaskId])

  useEffect(() => {
    if (taskData?.fallback === true) {
      setFallbackDetected(true)
    }
  }, [taskData])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!diffInput.trim()) return

    submitMutation.mutate(
      { diff: diffInput },
      {
        onSuccess: (data: any) => {
          setActiveTaskId(data.task_id)
        }
      }
    )
  }

  const isAnalyzing = Boolean((isPolling && activeTaskId) || taskData?.status === 'processing' || taskData?.status === 'pending')
  const isCompleted = taskData?.status === 'completed'
  const isFailed = taskData?.status === 'failed'
  const issues = taskData?.result?.issues || []

  return (
    <div className="space-y-6 flex flex-col h-[calc(100vh-8rem)]">
      <div className="flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Review Engine</h1>
          <p className="text-muted-foreground">Interactive AI diff review and telemetry feedback.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 flex-1 min-h-0">
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

        <div className="flex flex-col gap-4 border border-border rounded-lg bg-card p-4 relative min-h-0 shadow-sm">
          <div className="flex items-center gap-2 text-sm font-medium border-b border-border pb-2 shrink-0">
            Results & Telemetry
            {isAnalyzing && (
              <span className="ml-auto text-xs font-semibold text-primary animate-pulse tracking-wide">
                AI processing task {activeTaskId?.slice(0, 6)}...
              </span>
            )}
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
              {timeoutReached ? (
                <div className="flex flex-col items-center justify-center gap-3 text-yellow-600 bg-yellow-100 border border-yellow-300 rounded p-4">
                  <AlertCircle className="h-8 w-8" />
                  <span className="font-semibold">Analysis is taking longer than expected.</span>
                  <span className="text-sm">If this persists, please check your backend worker or try again later.</span>
                </div>
              ) : fallbackDetected ? (
                <div className="flex flex-col items-center justify-center gap-3 text-orange-600 bg-orange-100 border border-orange-300 rounded p-4">
                  <AlertCircle className="h-8 w-8" />
                  <span className="font-semibold">Backend is in fallback mode.</span>
                  <span className="text-sm">The backend could not process your request normally. Please check your API keys, backend logs, or try again later.</span>
                </div>
              ) : (
                <>
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
                </>
              )}
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

export default ReviewEngine
