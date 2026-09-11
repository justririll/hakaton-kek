/** Тонкая обёртка над REST API аналитического сервиса. */

async function get(path, params) {
  const query = params ? '?' + new URLSearchParams(params) : ''
  const response = await fetch(`/api${path}${query}`)
  if (!response.ok) {
    const detail = await response.text()
    throw new Error(`${response.status} ${path}: ${detail.slice(0, 200)}`)
  }
  return response.json()
}

export const api = {
  health: () => get('/health'),
  meta: () => get('/meta'),
  overview: () => get('/overview'),
  organizations: () => get('/organizations'),
  organization: (id) => get(`/organizations/${encodeURIComponent(id)}`),
  clusters: () => get('/clusters'),
  validation: () => get('/clusters/validation'),
  recommendations: (params) => get('/recommendations', params),
  plan: () => get('/plan'),
  anomalies: (params) => get('/anomalies', params),
  quality: () => get('/quality'),
  benchmark: (metric) => get(`/benchmark/${metric}`),
  aiStatus: () => get('/ai/status'),
  aiSummary: (refresh = false) => get('/ai/summary', refresh ? { refresh: 'true' } : undefined),
  aiOrgSummary: (orgId, refresh = false) => get(`/ai/org/${encodeURIComponent(orgId)}`, refresh ? { refresh: 'true' } : undefined),
}
