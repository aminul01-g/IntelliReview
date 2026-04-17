import axios, { AxiosResponse, AxiosError } from 'axios'

export const api = axios.create({
  baseURL: (import.meta as any).env.VITE_API_BASE_URL || '/api',
  withCredentials: true, // Required for HttpOnly cookies
})

// ── Response interceptor ───────────────────────────────────────────────────────

api.interceptors.response.use(
  (response: AxiosResponse) => response,

  async (error: AxiosError) => {
    const originalRequest: any = error.config
    const status: number | undefined = error.response?.status
    const data = error.response?.data ?? {}

    // ── 1. 401 — token refresh flow ──────────────────────────────────────────
    if (status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      try {
        await axios.post('/api/auth/refresh', {}, { withCredentials: true })
        return api(originalRequest)
      } catch (refreshError) {
        window.dispatchEvent(new Event('auth:unauthorized'))
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
    if (!status || status >= 500) {
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
