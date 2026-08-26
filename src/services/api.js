const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api'

async function request(path, options = {}) {
  const token = localStorage.getItem('sacco_auth_token')
  const headers = { ...(token ? { Authorization: `Token ${token}` } : {}), ...options.headers }
  if (!(options.body instanceof FormData)) headers['Content-Type'] = 'application/json'
  const response = await fetch(`${API_URL}${path}`, {
    headers,
    ...options,
  })
  if (!response.ok) {
    const error = new Error(`Request failed with status ${response.status}`)
    error.status = response.status
    throw error
  }
  return response.json()
}

export function getDashboard() {
  return request('/dashboard/me/')
}

export function getTransactions() {
  return request('/transactions/')
}

export function getLoanTerms() {
  return request('/loans/terms/')
}

export function getLoans() {
  return request('/loans/')
}

export function applyForLoan(loanAmount) {
  return request('/loans/', { method: 'POST', body: JSON.stringify({ loan_amount: loanAmount }) })
}

export function cancelLoan(loanId) {
  return request(`/loans/${loanId}/cancel/`, { method: 'POST' })
}

export function createSavings(payload) {
  return request('/savings/', { method: 'POST', body: JSON.stringify(payload) })
}

export function loginRequest(payload) {
  return request('/auth/login/', { method: 'POST', body: JSON.stringify(payload) })
}

export function registerRequest(payload) {
  return request('/auth/register/', { method: 'POST', body: JSON.stringify(payload) })
}

export function getProfile() {
  return request('/profile/me/')
}

export function updateProfile(payload) {
  return request('/profile/me/', { method: 'PATCH', body: JSON.stringify(payload) })
}

export function uploadProfilePicture(file) {
  const formData = new FormData()
  formData.append('profile_picture', file)
  return request('/profile/me/profile-picture/', { method: 'POST', headers: {}, body: formData })
}

export function changePassword(payload) {
  return request('/auth/change-password/', { method: 'POST', body: JSON.stringify(payload) })
}

export function getPaymentConfig() {
  return request('/payment-config/')
}

export function startPayment(payload) {
  return request('/payments/start/', { method: 'POST', body: JSON.stringify(payload) })
}

export function getAdminDashboard() {
  return request('/admin/dashboard/')
}

export function getAdminPayments() {
  return request('/payments/')
}

export function getAdminMembers(search = '') {
  return request(`/admin/members/${search ? `?search=${encodeURIComponent(search)}` : ''}`)
}

export function getAdminLoans() {
  return request('/loans/')
}

export function adminPaymentAction(paymentId, action, reason = '') {
  return request(`/admin/payments/${paymentId}/action/`, { method: 'POST', body: JSON.stringify({ action, reason }) })
}

export function adminLoanAction(loanId, action, reason = '') {
  return request(`/admin/loans/${loanId}/action/`, { method: 'POST', body: JSON.stringify({ action, reason }) })
}

export function getNotices() { return request('/notices/') }
export function getAdminNotices() { return request('/admin/notices/') }
export function createAdminNotice(payload) { return request('/admin/notices/', { method: 'POST', body: JSON.stringify(payload) }) }
export function generateLoanNotices(kind) { return request('/admin/loan-notices/generate/', { method: 'POST', body: JSON.stringify({ kind }) }) }
export function blockMember(memberId, blocked = true) { return request(`/admin/members/${memberId}/block/`, { method: 'POST', body: JSON.stringify({ blocked }) }) }
export function getAdminAudit() { return request('/admin/audit/') }
export function getAdminSettings() { return request('/admin/sacco-settings/') }
export function updateAdminSettings(payload) { return request('/admin/sacco-settings/', { method: 'PUT', body: JSON.stringify(payload) }) }
