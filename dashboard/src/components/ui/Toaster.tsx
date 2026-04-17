/**
 * Toaster — renders all active toast notifications.
 *
 * Mounts as a portal at the top-right corner.
 * The `engine_error` variant has its own distinct design to
 * make Analysis Engine unavailability unmistakably clear.
 */
import React, { useEffect, useState } from 'react'
import { useToast, Toast } from '../../contexts/ToastContext'

// ── Icons (inline SVG keeps zero extra deps) ─────────────────────────────────

const IconCheck = () => (
  <svg viewBox="0 0 20 20" fill="currentColor" className="h-5 w-5">
    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
  </svg>
)
const IconX = () => (
  <svg viewBox="0 0 20 20" fill="currentColor" className="h-5 w-5">
    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
  </svg>
)
const IconWarn = () => (
  <svg viewBox="0 0 20 20" fill="currentColor" className="h-5 w-5">
    <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
  </svg>
)
const IconInfo = () => (
  <svg viewBox="0 0 20 20" fill="currentColor" className="h-5 w-5">
    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
  </svg>
)
const IconEngine = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-5 w-5">
    <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17H3a2 2 0 01-2-2V5a2 2 0 012-2h14a2 2 0 012 2v10a2 2 0 01-2 2h-2" />
  </svg>
)
const IconClose = () => (
  <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
    <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 011.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
  </svg>
)

// ── Variant styles ────────────────────────────────────────────────────────────

const VARIANTS: Record<Toast['type'], { bg: string; border: string; icon: React.ReactNode; iconColor: string }> = {
  success:      { bg: 'bg-card', border: 'border-green-500/40',      icon: <IconCheck />,  iconColor: 'text-green-400' },
  error:        { bg: 'bg-card', border: 'border-destructive/40',    icon: <IconX />,      iconColor: 'text-destructive' },
  warning:      { bg: 'bg-card', border: 'border-amber-500/40',      icon: <IconWarn />,   iconColor: 'text-amber-400' },
  info:         { bg: 'bg-card', border: 'border-primary/30',        icon: <IconInfo />,   iconColor: 'text-primary' },
  engine_error: { bg: 'bg-[#1a0f0f]', border: 'border-red-700/60',  icon: <IconEngine />, iconColor: 'text-red-400' },
}

// ── Countdown hook for retry-after toasts ────────────────────────────────────

function useCountdown(seconds?: number) {
  const [remaining, setRemaining] = useState(seconds ?? 0)
  useEffect(() => {
    if (!seconds) return
    setRemaining(seconds)
    const interval = setInterval(() => {
      setRemaining(r => (r <= 1 ? 0 : r - 1))
    }, 1000)
    return () => clearInterval(interval)
  }, [seconds])
  return remaining
}

// ── Single toast card ─────────────────────────────────────────────────────────

function ToastCard({ toast }: { toast: Toast }) {
  const { dismiss } = useToast()
  const countdown = useCountdown(toast.retryAfter)
  const v = VARIANTS[toast.type]

  const isEngine = toast.type === 'engine_error'

  return (
    <div
      className={`
        relative flex items-start gap-3 w-80 rounded-xl border px-4 py-3 shadow-2xl
        backdrop-blur-sm animate-in slide-in-from-right-5 duration-300
        ${v.bg} ${v.border}
        ${isEngine ? 'ring-1 ring-red-800/50' : ''}
      `}
      role="alert"
      aria-live="assertive"
    >
      {/* Icon */}
      <span className={`mt-0.5 shrink-0 ${v.iconColor}`}>{v.icon}</span>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p className={`text-sm font-semibold leading-snug ${isEngine ? 'text-red-300' : 'text-foreground'}`}>
          {toast.title}
        </p>
        {toast.message && (
          <p className={`text-xs mt-0.5 leading-relaxed ${isEngine ? 'text-red-400/80' : 'text-muted-foreground'}`}>
            {toast.message}
          </p>
        )}
        {isEngine && countdown > 0 && (
          <p className="text-xs mt-1.5 text-red-500 font-mono">
            Retrying automatically in {countdown}s…
          </p>
        )}
        {isEngine && countdown === 0 && toast.retryAfter && (
          <p className="text-xs mt-1.5 text-red-500/70">
            Retry attempts exhausted. Check worker logs.
          </p>
        )}
      </div>

      {/* Dismiss */}
      <button
        onClick={() => dismiss(toast.id)}
        className="shrink-0 mt-0.5 p-0.5 rounded text-muted-foreground hover:text-foreground hover:bg-muted/40 transition-colors"
        aria-label="Dismiss notification"
      >
        <IconClose />
      </button>

      {/* Progress bar for auto-dismiss toasts */}
      {toast.duration && toast.duration > 0 && !isEngine && (
        <div
          className="absolute bottom-0 left-0 h-0.5 rounded-b-xl bg-primary/40"
          style={{ animation: `shrink-width ${toast.duration}ms linear forwards` }}
        />
      )}
    </div>
  )
}

// ── Toaster portal ────────────────────────────────────────────────────────────

export function Toaster() {
  const { toasts } = useToast()

  if (toasts.length === 0) return null

  return (
    <div
      className="fixed top-4 right-4 z-[9999] flex flex-col gap-3"
      aria-label="Notifications"
    >
      {toasts.map((t: Toast) => <ToastCard key={t.id} toast={t} />)}
    </div>
  )
}
