import React, { useState, useEffect, useRef } from 'react'
import * as Lucide from 'lucide-react'

const { FileCode, Play, AlertCircle, CheckCircle, Code, GitBranch } = Lucide as any
import { useSubmitAnalysis, useAnalysisTaskStatus, useSubmitSnippetAnalysis, isDiffFormat, guessLanguage } from '@/hooks/useAnalysisTask'
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
        rule_id: suggestion.rule_id || suggestion.id || suggestion.concept || 'UNKNOWN_RULE',
        action,
        task_id: taskId,
        line_number: suggestion.line || 0
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
        finding_id: suggestion.rule_id || suggestion.id || suggestion.concept || 'UNKNOWN',
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
        finding_id: suggestion.rule_id || suggestion.id || suggestion.concept || 'UNKNOWN',
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
          <h3 className="text-sm font-semibold text-foreground">{suggestion.title || suggestion.concept || 'Technical Debt Finding'}</h3>
          <p className="text-xs text-muted-foreground mt-1">Severity: {suggestion.severity || suggestion.rule_id || suggestion.id || 'N/A'}</p>
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

  // Dual-mode: snippet analysis (synchronous) vs diff review (async/polling)
  const [snippetResult, setSnippetResult] = useState<any>(null)
  const [snippetError, setSnippetError] = useState<string | null>(null)

  const submitDiffMutation = useSubmitAnalysis()
  const submitSnippetMutation = useSubmitSnippetAnalysis()
  const { data: taskData, isLoading: isPolling } = useAnalysisTaskStatus(activeTaskId)

  // Auto-detect mode from input
  const detectedMode = diffInput.trim() ? (isDiffFormat(diffInput) ? 'diff' : 'snippet') : null
  const detectedLanguage = detectedMode === 'snippet' ? guessLanguage(diffInput) : null

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

    // Reset previous results
    setSnippetResult(null)
    setSnippetError(null)
    setActiveTaskId(null)

    if (isDiffFormat(diffInput)) {
      // ── Diff mode: async via Celery/fallback ──
      submitDiffMutation.mutate(
        { diff: diffInput },
        {
          onSuccess: (data: any) => {
            setActiveTaskId(data.task_id)
          }
        }
      )
    } else {
      // ── Snippet mode: synchronous full static analysis ──
      const language = guessLanguage(diffInput)
      submitSnippetMutation.mutate(
        { code: diffInput, language, filename: `review.${language === 'python' ? 'py' : language === 'javascript' ? 'js' : language === 'java' ? 'java' : 'py'}` },
        {
          onSuccess: (data: any) => {
            setSnippetResult(data)
          },
          onError: (error: any) => {
            setSnippetError(error?.response?.data?.detail || error?.message || 'Analysis failed')
          }
        }
      )
    }
  }

  // ── Compute display state from either mode ──
  const isSubmitting = submitDiffMutation.isPending || submitSnippetMutation.isPending
  const isAnalyzingDiff = Boolean((isPolling && activeTaskId) || taskData?.status === 'processing' || taskData?.status === 'PENDING')
  const isAnalyzing = isSubmitting || isAnalyzingDiff

  // Diff mode results
  const diffCompleted = taskData?.status === 'SUCCESS' || taskData?.status === 'completed'
  const diffFailed = taskData?.status === 'FAILURE' || taskData?.status === 'failed'
  const diffIssues = taskData?.result?.findings || taskData?.result?.issues || []
  const diffVerdict = taskData?.result?.verdict
  const diffDebtHours = taskData?.result?.total_debt_hours

  // Snippet mode results
  const snippetCompleted = snippetResult !== null
  const snippetIssues = snippetResult?.issues || []
  const snippetMetrics = snippetResult?.metrics

  // Unified state
  const hasResults = snippetCompleted || diffCompleted
  const hasFailed = diffFailed || snippetError !== null
  const issues = snippetCompleted ? snippetIssues : diffIssues
  const verdict = snippetCompleted
    ? (snippetIssues.length > 0
        ? `Found ${snippetIssues.length} issue${snippetIssues.length !== 1 ? 's' : ''} across ${snippetMetrics?.lines_of_code ?? '?'} lines of code.`
        : 'No issues found — code looks clean.')
    : diffVerdict
  const totalDebtHours = snippetCompleted ? undefined : diffDebtHours

  return (
    <div className="space-y-6 flex flex-col h-[calc(100vh-8rem)]">
      <div className="flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Review Engine</h1>
          <p className="text-muted-foreground">Paste code or a git diff for instant security and quality analysis.</p>
        </div>
        {detectedMode && (
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold border transition-colors ${
            detectedMode === 'snippet'
              ? 'bg-blue-500/10 text-blue-500 border-blue-500/30'
              : 'bg-purple-500/10 text-purple-500 border-purple-500/30'
          }`}>
            {detectedMode === 'snippet' ? <Code className="h-3.5 w-3.5" /> : <GitBranch className="h-3.5 w-3.5" />}
            {detectedMode === 'snippet' ? `Code Snippet · ${detectedLanguage}` : 'Unified Diff'}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 flex-1 min-h-0">
        <div className="flex flex-col gap-4 border border-border rounded-lg bg-card p-4 min-h-0">
          <div className="flex items-center gap-2 text-sm font-medium border-b border-border pb-2 shrink-0">
            <FileCode className="h-4 w-4" /> Code / Diff Input
          </div>
          <form onSubmit={handleSubmit} className="flex-1 flex flex-col gap-4 min-h-0">
            <textarea
              className="flex-1 bg-background border border-input rounded-md p-3 text-sm font-mono text-foreground focus:outline-none focus:ring-1 focus:ring-ring resize-none leading-relaxed"
              placeholder={"Paste Python, JavaScript, Java, or C++ code here...\n\nOr paste a unified diff (git diff output) for tech debt review.\n\nThe engine auto-detects the input format."}
              value={diffInput}
              onChange={(e) => setDiffInput(e.target.value)}
              disabled={isAnalyzing}
            />
            <button
              type="submit"
              disabled={isAnalyzing || !diffInput.trim()}
              className="shrink-0 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2 rounded-md font-medium text-sm flex items-center justify-center gap-2 transition-colors disabled:opacity-50 shadow-sm"
            >
              {isAnalyzing ? (
                <div className="h-4 w-4 rounded-full border-2 border-primary-foreground border-t-transparent animate-spin" />
              ) : (
                <Play className="h-4 w-4 fill-current" />
              )}
              {isAnalyzing ? 'Analyzing...' : 'Run Security Analysis'}
            </button>
          </form>
        </div>

        <div className="flex flex-col gap-4 border border-border rounded-lg bg-card p-4 relative min-h-0 shadow-sm">
          <div className="flex items-center gap-2 text-sm font-medium border-b border-border pb-2 shrink-0">
            Results & Telemetry
            {isAnalyzingDiff && (
              <span className="ml-auto text-xs font-semibold text-primary animate-pulse tracking-wide">
                AI processing task {activeTaskId?.slice(0, 6)}...
              </span>
            )}
          </div>

          {!hasResults && !hasFailed && !isAnalyzing ? (
            <div className="flex-1 flex items-center justify-center text-muted-foreground text-sm flex-col gap-3">
              <div className="h-12 w-12 rounded-full bg-muted/50 flex items-center justify-center mb-2">
                <FileCode className="h-6 w-6 opacity-40" />
              </div>
              Waiting for input...
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
          ) : hasFailed ? (
            <div className="flex-1 flex items-center justify-center text-destructive flex-col gap-2">
              <AlertCircle className="h-10 w-10 mb-2 opacity-80" />
              <span className="font-semibold text-lg tracking-tight">Analysis Failed</span>
              <span className="text-sm opacity-80">{snippetError || 'The backend worker encountered an error.'}</span>
            </div>
          ) : hasResults ? (
            <div className="flex-1 flex flex-col gap-4 overflow-hidden">
              <div className="bg-green-500/10 text-green-500 border border-green-500/20 rounded-md p-3 text-sm flex items-start gap-2 shrink-0">
                <CheckCircle className="h-5 w-5 shrink-0 mt-0.5" />
                <div>
                  <p className="font-semibold">Analysis Complete</p>
                  <p className="opacity-90 mt-0.5 text-xs">
                    {issues.length > 0
                      ? `Found ${issues.length} issue${issues.length !== 1 ? 's' : ''}. Review and provide feedback below.`
                      : 'No issues detected.'}
                  </p>
                </div>
              </div>
              {verdict && (
                <div className={`${issues.length > 0 ? 'bg-amber-500/10 text-amber-500 border-amber-500/20' : 'bg-blue-500/10 text-blue-500 border-blue-500/20'} border rounded-md p-3 text-sm flex items-start gap-2 shrink-0`}>
                  <div className="flex-1">
                    <p className="font-semibold">Analysis Summary</p>
                    <p className="opacity-90 mt-0.5">{verdict}</p>
                    {snippetMetrics && (
                      <p className="opacity-80 mt-1 text-xs">
                        Lines: {snippetMetrics.lines_of_code} · Complexity: {snippetMetrics.complexity ?? 'N/A'} · Maintainability: {snippetMetrics.maintainability_index?.toFixed(1) ?? 'N/A'}
                      </p>
                    )}
                    {totalDebtHours !== undefined && (
                      <p className="opacity-80 mt-1 text-xs">Estimated technical debt: {totalDebtHours} hours</p>
                    )}
                  </div>
                </div>
              )}
              <div className="flex-1 overflow-auto space-y-4 pr-1 custom-scrollbar">
                {issues.length === 0 ? (
                  <div className="text-muted-foreground text-sm text-center py-8">
                    {verdict ? "Analysis completed successfully. No issues detected." : "No issues found in this analysis."}
                  </div>
                ) : (
                  issues.map((issue: any, index: number) => (
                    <SuggestionCard key={index} suggestion={issue} taskId={activeTaskId ?? undefined} />
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
