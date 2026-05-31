import { reactive } from 'vue'
import { http, getToken, setToken } from '../api/client'

export const authState = reactive({
  token: getToken(),
  user: null,
  loading: false,
})

export async function loadMe() {
  if (!authState.token) return null
  authState.loading = true
  try {
    const data = await http.get('/api/auth/me')
    authState.user = data.user
    return data.user
  } finally {
    authState.loading = false
  }
}

export async function login(username, password) {
  const data = await http.post('/api/auth/login', { username, password })
  setToken(data.token)
  authState.token = data.token
  authState.user = data.user
  return data
}

export async function logout() {
  try {
    await http.post('/api/auth/logout')
  } finally {
    setToken(null)
    authState.token = null
    authState.user = null
  }
}

export function isAuthed() {
  return Boolean(authState.token)
}
