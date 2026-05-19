import axios, { AxiosResponse, AxiosError } from 'axios'

// VITE_API_BASE_URL is already the full base, e.g. http://localhost:7860/api/v1
// In production (when the SPA is served by FastAPI), we fall back to /api/v1
const baseURL =
  (import.meta as any).env.VITE_API_BASE_URL ?? '/api/v1'

export const api = axios.create({
  baseURL,
  withCredentials: true, // Required for HttpOnly cookies
})

// ── Request interceptor ────────────────────────────────────────────────────────
// Always attach the token from localStorage to every outgoing request.
// This is essential because axios defaults.headers are lost on page reload,
// and HttpOnly cookies may not be sent on certain cross-origin/HTTPS setups.
api.interceptors.request.use((config: any) => {
  const token = localStorage.getItem('auth_token')
  if (token && !config.headers['Authorization']) {
    config.headers['Authorization'] = `Bearer ${token}`
  }
  return config
})

// ── Response interceptor ───────────────────────────────────────────────────────

api.interceptors.response.use(
  (response: AxiosResponse) => response,

  async (error: AxiosError) => {
    const originalRequest: any = error.config
    const status: number | undefined = error.response?.status
    const data: any = error.response?.data ?? {}

    // ── 1. 401 — session expired / not authenticated ─────────────────────────
    if (status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      // If there's no token at all, the user never logged in — skip refresh
      const token = localStorage.getItem('auth_token')
      if (!token) {
        window.dispatchEvent(new Event('auth:unauthorized'))
        return Promise.reject(error)
      }

      try {
        // Attempt to silently refresh using the expired token
        const { data: refreshData } = await api.post('/auth/refresh', {}, {
          headers: { Authorization: `Bearer ${token}` }
        })

        if (refreshData?.access_token) {
          localStorage.setItem('auth_token', refreshData.access_token)

          // Retry the original request with the new token
          originalRequest.headers['Authorization'] = `Bearer ${refreshData.access_token}`
          return api(originalRequest)
        }
      } catch (refreshError: any) {
        // Refresh failed — session is truly dead, clear stale token
        localStorage.removeItem('auth_token')
        // Only broadcast unauthorized if it was an auth failure, not a network error
        if (refreshError?.response?.status === 401 || !refreshError?.response) {
          window.dispatchEvent(new Event('auth:unauthorized'))
        }
        return Promise.reject(refreshError)
      }
    }

    // ── 2. LLM / Analysis Engine errors ─────────────────────────────────────
    // The backend middleware sets `error_code` in the body and an
    // X-IntelliReview-Engine-Error header for these situations.
    const errorCode: string | undefined =
      data.error_code ??
      error.response?.headers?.['x-intellireview-engine-error']

    if (errorCode) {
      const toastDetail = {
        error_code: errorCode,
        title: _engineErrorTitle(errorCode),
        message: data.message ?? 'The Analysis Engine encountered an upstream error.',
        retryAfter: data.retry_after ?? undefined,
      }

      // Broadcast so any mounted ToastProvider can display it without
      // needing direct access to the toast() function here.
      window.dispatchEvent(
        new CustomEvent('intellireview:engine-error', { detail: toastDetail })
      )

      return Promise.reject(error)
    }

    // ── 3. Generic network / 5xx passthrough ────────────────────────────────
    // Exclude 401 to avoid spurious "engine unavailable" toasts during auth checks.
    if (status && status >= 500) {
      window.dispatchEvent(
        new CustomEvent('intellireview:engine-error', {
          detail: {
            error_code: 'LLM_UNAVAILABLE',
            title: 'Analysis Engine Unavailable',
            message: 'Could not reach the analysis service. Please try again shortly.',
          }
        })
      )
    }

    return Promise.reject(error)
  }
)

function _engineErrorTitle(code: string): string {
  switch (code) {
    case 'LLM_RATE_LIMITED': return 'Analysis Engine Rate Limited'
    case 'LLM_TIMEOUT':      return 'Analysis Engine Timed Out'
    default:                  return 'Analysis Engine Unavailable'
  }
}
