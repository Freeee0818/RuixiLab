import { reactive } from 'vue'
import { API_SERVICES } from './api/config'

export const accessControlEnabled = import.meta.env.VITE_ACCESS_CONTROL_ENABLED === 'true'

export const accessState = reactive({
  checked: false,
  loading: false,
  authenticated: !accessControlEnabled,
  source: accessControlEnabled ? 'none' : 'disabled',
  role: accessControlEnabled ? 'guest' : 'admin',
  username: '',
  displayName: '',
  email: '',
  isAdmin: !accessControlEnabled,
  adminEmail: 'wangcheng308@bupt.edu.cn',
  clientIp: '',
})

let sessionPromise = null

function authUrl(path) {
  return `${String(API_SERVICES.ACCESS.baseURL || '/auth').replace(/\/$/, '')}${path}`
}

async function request(path, options = {}) {
  const response = await fetch(authUrl(path), {
    credentials: 'include',
    cache: 'no-store',
    ...options,
    headers: {
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...(options.headers || {}),
    },
  })
  const contentType = response.headers.get('content-type') || ''
  const payload = contentType.includes('application/json') ? await response.json() : null
  if (!response.ok) {
    const error = new Error(payload?.detail || `请求失败 (${response.status})`)
    error.status = response.status
    error.payload = payload
    throw error
  }
  return payload || {}
}

function applySession(payload) {
  accessState.checked = true
  accessState.authenticated = Boolean(payload.authenticated)
  accessState.source = payload.source || 'none'
  accessState.role = payload.role || 'guest'
  accessState.username = payload.username || ''
  accessState.displayName = payload.display_name || ''
  accessState.email = payload.email || ''
  accessState.isAdmin = Boolean(payload.is_admin)
  accessState.adminEmail = payload.admin_email || accessState.adminEmail
  accessState.clientIp = payload.client_ip || ''
}

export async function refreshAccessSession({ force = false } = {}) {
  if (!accessControlEnabled) {
    accessState.checked = true
    return accessState
  }
  if (accessState.checked && !force) return accessState
  if (sessionPromise && !force) return sessionPromise

  accessState.loading = true
  sessionPromise = request('/session')
    .then((payload) => {
      applySession(payload)
      return accessState
    })
    .catch(() => {
      applySession({ authenticated: false, admin_email: accessState.adminEmail })
      return accessState
    })
    .finally(() => {
      accessState.loading = false
      sessionPromise = null
    })
  return sessionPromise
}

export async function loginAccess(identifier, password) {
  await request('/login', {
    method: 'POST',
    body: JSON.stringify({ identifier, password }),
  })
  return refreshAccessSession({ force: true })
}

export async function logoutAccess() {
  await request('/logout', { method: 'POST' })
  applySession({ authenticated: false, admin_email: accessState.adminEmail })
}

export function markAccessExpired() {
  if (!accessControlEnabled) return
  applySession({ authenticated: false, admin_email: accessState.adminEmail })
}

export async function listAccessAccounts() {
  return request('/admin/accounts')
}

export async function listAccessClasses() {
  return request('/admin/classes')
}

export async function createAccessClass(name) {
  return request('/admin/classes', { method: 'POST', body: JSON.stringify({ name }) })
}

export async function listAccessClassAccounts(classId) {
  return request(`/admin/classes/${encodeURIComponent(classId)}/accounts`)
}

export async function createAccessAccount(payload) {
  return request('/admin/accounts', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function updateAccessAccount(username, payload) {
  return request(`/admin/accounts/${encodeURIComponent(username)}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}
