let cachedToken: string | null =
  (typeof window !== 'undefined' && (window as any).__AETHER_BOOTSTRAP__?.token) ||
  (typeof window !== 'undefined' ? localStorage.getItem('aether_auth_token') : null)

export async function getAuthToken(): Promise<string> {
  if (cachedToken) return cachedToken

  // Check window bootstrap object first
  if (typeof window !== 'undefined' && (window as any).__AETHER_BOOTSTRAP__?.token) {
    cachedToken = (window as any).__AETHER_BOOTSTRAP__.token
    if (cachedToken) {
      localStorage.setItem('aether_auth_token', cachedToken)
      return cachedToken
    }
  }

  // Check localStorage
  const stored = typeof window !== 'undefined' ? localStorage.getItem('aether_auth_token') : null
  if (stored) {
    cachedToken = stored
    return stored
  }

  return ''
}

export function setAuthToken(token: string) {
  cachedToken = token
  if (typeof window !== 'undefined') {
    localStorage.setItem('aether_auth_token', token)
  }
}

export async function apiFetch<T>(url: string, options: RequestInit = {}): Promise<T> {
  let token = await getAuthToken()
  const headers = new Headers(options.headers || {})

  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`)
  }
  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }

  let response = await fetch(url, { ...options, headers })

  // If 401, refresh token from /api/auth/token and retry once
  if (response.status === 401) {
    localStorage.removeItem('aether_auth_token')
    cachedToken = null
    token = await getAuthToken()
    if (token) {
      headers.set('Authorization', `Bearer ${token}`)
      response = await fetch(url, { ...options, headers })
    }
  }

  if (!response.ok) {
    let errorDetail = response.statusText
    try {
      const errJson = await response.json()
      errorDetail = errJson.detail || JSON.stringify(errJson)
    } catch {
      // ignore
    }
    throw new Error(`API error [${response.status}]: ${errorDetail}`)
  }

  return response.json() as Promise<T>
}
