import React, { Component } from 'react'
import type { ErrorInfo } from 'react'
import { AlertCircle } from 'lucide-react'

interface Props {
  children: React.ReactNode
  label?: string
}

interface State {
  hasError: boolean
  errorMessage: string | null
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, errorMessage: null }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, errorMessage: error.message }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    const label = this.props.label ?? 'Component'
    console.error(`[ErrorBoundary:${label}]`, error, info.componentStack)
    window.dispatchEvent(
      new CustomEvent('intellireview:engine-error', {
        detail: { title: `${label} crashed`, message: error.message },
      })
    )
  }

  handleReset = (): void => {
    this.setState({ hasError: false, errorMessage: null })
  }

  render() {
    const { label, children } = this.props

    if (!this.state.hasError) return children

    return (
      <div className="flex items-center justify-center h-full min-h-[300px] p-8">
        <div className="bg-[#1a0f0f] border border-red-800/50 rounded-2xl p-8 max-w-md w-full shadow-2xl ring-1 ring-red-900/30 text-center space-y-4">
          <div className="mx-auto h-14 w-14 rounded-full bg-red-900/30 flex items-center justify-center">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="h-7 w-7 text-red-400">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
            </svg>
          </div>

          <div>
            <h2 className="text-lg font-bold text-red-300">{label ?? 'Component'} Unavailable</h2>
            <p className="text-sm text-red-400/70 mt-1">
              The Analysis Engine encountered an unexpected error and could not render this view.
            </p>
          </div>

          {this.state.errorMessage && (
            <details className="text-left">
              <summary className="text-xs text-red-500/60 cursor-pointer hover:text-red-400 transition-colors">
                View error details
              </summary>
              <pre className="mt-2 text-xs text-red-400/50 font-mono whitespace-pre-wrap break-all bg-black/30 rounded p-3">
                {this.state.errorMessage}
              </pre>
            </details>
          )}

          <div className="flex gap-3 justify-center">
            <button
              onClick={this.handleReset}
              className="px-4 py-2 text-sm font-medium rounded-lg bg-red-900/40 hover:bg-red-900/60 text-red-300 border border-red-800/50 transition-colors"
            >
              Try Again
            </button>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 text-sm font-medium rounded-lg bg-muted/30 hover:bg-muted/50 text-muted-foreground border border-border/50 transition-colors"
            >
              Reload Page
            </button>
          </div>
        </div>
      </div>
    )
  }
}
