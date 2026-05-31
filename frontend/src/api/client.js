const API_BASE = import.meta.env.VITE_API_BASE || ''
const TOKEN_KEY = 'lexy_lab_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

export async function api(path, options = {}) {
  const headers = new Headers(options.headers || {})
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const isForm = options.body instanceof FormData
  if (!isForm && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers })
  const contentType = response.headers.get('content-type') || ''
  const payload = contentType.includes('application/json') ? await response.json() : await response.text()
  if (!response.ok) {
    const message = payload?.message || '请求失败'
    const error = new Error(message)
    error.code = payload?.code
    error.status = response.status
    throw error
  }
  return payload.data
}

export const http = {
  get: (path) => api(path),
  post: (path, body = {}) =>
    api(path, {
      method: 'POST',
      body: body instanceof FormData ? body : JSON.stringify(body),
    }),
  patch: (path, body = {}) => api(path, { method: 'PATCH', body: JSON.stringify(body) }),
  delete: (path, body = {}) => api(path, { method: 'DELETE', body: JSON.stringify(body) }),
}
