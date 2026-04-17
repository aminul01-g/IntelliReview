import React from 'react'
import ReactDOM from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AppShell } from './components/layout/AppShell'
import { Dashboard } from './pages/Dashboard'
import { ScanHistory } from './pages/ScanHistory'
import { RulesStudio } from './pages/RulesStudio'
import { ReviewEngine } from './pages/ReviewEngine'
import { AuthProvider } from './contexts/AuthContext'
import { ProtectedRoute } from './components/layout/ProtectedRoute'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

const router = createBrowserRouter([
  {
    path: "/",
    element: (
      <AuthProvider>
        <AppShell />
      </AuthProvider>
    ),
    children: [
      {
        index: true,
        element: <Dashboard />,
      },
      {
        path: "history",
        element: <ScanHistory />,
      },
      {
        path: "review",
        element: <ReviewEngine />,
      },
      // Protected Route for Custom Rules Studio (Admin or Reviewer only)
      {
        element: <ProtectedRoute allowedRoles={['Admin', 'Reviewer']} />,
        children: [
          {
            path: "rules",
            element: <RulesStudio />,
          },
        ],
      },
    ],
  },
]);

ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
        <QueryClientProvider client={queryClient}>
            <RouterProvider router={router} />
        </QueryClientProvider>
    </React.StrictMode>,
)
