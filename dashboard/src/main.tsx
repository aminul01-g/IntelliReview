import React, { useEffect } from 'react'
import * as ReactDOM from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AppShell } from './components/layout/AppShell'
import { Dashboard } from './pages/Dashboard'
import { ScanHistory } from './pages/ScanHistory'
import { RulesStudio } from './pages/RulesStudio'
import { ReviewEngine } from './pages/ReviewEngine'
import { Login } from './pages/Login'
import { UploadProject } from './pages/UploadProject'
import { MetricsView } from './pages/MetricsView'
import { ProfileSettings } from './components/profile/ProfileSettings'
import { AuthProvider } from './contexts/AuthContext'
import { ToastProvider, useToast } from './contexts/ToastContext'
import { ProtectedRoute } from './components/layout/ProtectedRoute'
import { Toaster } from './components/ui/Toaster'
import { ErrorBoundary } from './components/ui/ErrorBoundary'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

/**
 * EngineErrorBridge — listens for the global `intellireview:engine-error`
 * CustomEvent dispatched by api.ts and ErrorBoundary, then forwards it into
 * the ToastContext. Must be mounted inside <ToastProvider>.
 */
function EngineErrorBridge() {
  const { toast } = useToast() as any

  useEffect(() => {
    function handleEngineError(e: Event) {
      const detail = (e as CustomEvent).detail ?? {}
      toast({
        type: 'engine_error',
        title: detail.title ?? 'Analysis Engine Unavailable',
        message: detail.message,
        retryAfter: detail.retryAfter,
        duration: 0, // sticky until dismissed
      })
    }

    window.addEventListener('intellireview:engine-error', handleEngineError)
    return () => window.removeEventListener('intellireview:engine-error', handleEngineError)
  }, [toast])

  return null
}

const router = createBrowserRouter([
  {
    path: "/login",
    element: (
      <AuthProvider>
        <Login />
      </AuthProvider>
    ),
  },
  {
    path: "/",
    element: (
      <AuthProvider>
        <AppShell />
      </AuthProvider>
    ),
    children: [
      {
        element: <ProtectedRoute />,
        children: [
          {
            index: true,
            element: (
              <ErrorBoundary label="Dashboard">
                <Dashboard />
              </ErrorBoundary>
            ),
          },
          {
            path: "upload",
            element: (
              <ErrorBoundary label="Project Upload">
                <UploadProject />
              </ErrorBoundary>
            ),
          },
          {
            path: "review",
            element: (
              <ErrorBoundary label="Analysis Engine">
                <ReviewEngine />
              </ErrorBoundary>
            ),
          },
          {
            path: "history",
            element: (
              <ErrorBoundary label="Scan History">
                <ScanHistory />
              </ErrorBoundary>
            ),
          },
          {
            path: "metrics",
            element: (
              <ErrorBoundary label="Analytics & Metrics">
                <MetricsView />
              </ErrorBoundary>
            ),
          },
          {
            path: "profile",
            element: (
              <ErrorBoundary label="Profile Settings">
                <ProfileSettings />
              </ErrorBoundary>
            ),
          },
        ]
      },
      // Protected Route for Custom Rules Studio (Admin or Reviewer only)
      {
        element: <ProtectedRoute allowedRoles={['Admin', 'Reviewer']} />,
        children: [
          {
            path: "rules",
            element: (
              <ErrorBoundary label="Rules Studio">
                <RulesStudio />
              </ErrorBoundary>
            ),
          },
        ],
      },
    ],
  },
]);

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        {/* Bridge: translates window events → toast() calls */}
        <EngineErrorBridge />
        {/* Toast portal: renders in top-right corner above everything */}
        <Toaster />
        <RouterProvider router={router} />
      </ToastProvider>
    </QueryClientProvider>
  </React.StrictMode>,
)
