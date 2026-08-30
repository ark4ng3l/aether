let cachedToken: string | null =
  (typeof window !== 'undefined' && (window as any).__AETHER_BOOTSTRAP__?.token) ||
  (typeof window !== 'undefined' ? localStorage.getItem('aether_auth_token') : null)

export async function getAuthToken(): Promise<string> {
  if (cachedToken) return cachedToken

  if (typeof window !== 'undefined') {
    // 1. Check URL hash (e.g. #token=abc123...)
    if (window.location.hash) {
      const match = window.location.hash.match(/[#&]token=([a-zA-Z0-9_-]+)/)
      if (match && match[1]) {
        cachedToken = match[1]
        localStorage.setItem('aether_auth_token', cachedToken)
        return cachedToken
      }
    }

    // 2. Check URL search query parameter (e.g. ?token=abc123...)
    if (window.location.search) {
      const params = new URLSearchParams(window.location.search)
      const qToken = params.get('token')
      if (qToken) {
        cachedToken = qToken
        localStorage.setItem('aether_auth_token', cachedToken)
        return cachedToken
      }
    }

    // 3. Check window bootstrap object
    if ((window as any).__AETHER_BOOTSTRAP__?.token) {
      cachedToken = (window as any).__AETHER_BOOTSTRAP__.token
      if (cachedToken) {
        localStorage.setItem('aether_auth_token', cachedToken)
        return cachedToken
      }
    }

    // 4. Check localStorage
    const stored = localStorage.getItem('aether_auth_token')
    if (stored) {
      cachedToken = stored
      return stored
    }
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

  const contentType = response.headers.get('content-type') || ''
  if (contentType.includes('application/json')) {
    return response.json() as Promise<T>
  }
  return response.text() as unknown as Promise<T>
}

export async function apiFetchBlob(url: string, options: RequestInit = {}): Promise<Blob> {
  let token = await getAuthToken()
  const headers = new Headers(options.headers || {})

  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetch(url, { ...options, headers })
  if (!response.ok) {
    throw new Error(`API error [${response.status}]: ${response.statusText}`)
  }
  return response.blob()
}

