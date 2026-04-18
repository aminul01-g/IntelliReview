/**
 * ToastContext — global notification system for IntelliReview.
 *
 * Usage from any component:
 *   const { toast } = useToast()
 *   toast({ type: 'engine_error', title: '...', message: '...' })
 *
 * Special variant: type='engine_error' renders the distinctive
 * "Analysis Engine Unavailable" banner with retry countdown.
 */
import { createContext, useCallback, useContext, useReducer, useRef, ReactNode } from 'react'

export type ToastType = 'success' | 'error' | 'warning' | 'info' | 'engine_error'

export interface Toast {
  id: string
  type: ToastType
  title: string
  message?: string
  retryAfter?: number   // seconds, for rate-limit toasts
  duration?: number     // ms before auto-dismiss (0 = sticky)
}

interface ToastState { toasts: Toast[] }
type Action =
  | { type: 'ADD'; toast: Toast }
  | { type: 'REMOVE'; id: string }

function reducer(state: ToastState, action: Action): ToastState {
  switch (action.type) {
    case 'ADD':
      // Deduplicate: engine_error toasts are singletons
      if (action.toast.type === 'engine_error') {
        const exists = state.toasts.some(t => t.type === 'engine_error')
        if (exists) return state
      }
      return { toasts: [action.toast, ...state.toasts].slice(0, 5) }
    case 'REMOVE':
      return { toasts: state.toasts.filter(t => t.id !== action.id) }
    default:
      return state
  }
}

interface ToastContextValue {
  toasts: Toast[]
  toast: (opts: Omit<Toast, 'id'>) => void
  dismiss: (id: string) => void
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined)

export function ToastProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, { toasts: [] })
  const timers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map())

  const dismiss = useCallback((id: string) => {
    dispatch({ type: 'REMOVE', id })
    const t = timers.current.get(id)
    if (t) { clearTimeout(t); timers.current.delete(id) }
  }, [])

  const toast = useCallback((opts: Omit<Toast, 'id'>) => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
    const duration = opts.duration ?? (opts.type === 'engine_error' ? 0 : 6000)

    dispatch({ type: 'ADD', toast: { ...opts, id, duration } })

    if (duration > 0) {
      const timer = setTimeout(() => dismiss(id), duration)
      timers.current.set(id, timer)
    }
  }, [dismiss])

  return (
    <ToastContext.Provider value={{ toasts: state.toasts, toast, dismiss }}>
      {children}
    </ToastContext.Provider>
  )
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used inside <ToastProvider>')
  return ctx as ToastContextValue
}
