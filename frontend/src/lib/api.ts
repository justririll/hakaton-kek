/** Тонкая обёртка над REST API аналитического сервиса. */

import type {
  AiSummary, Anomaly, Clusters, Meta, Organization, OrgDetail,
  Overview, PlanRow, Quality, Recommendation, Validation,
} from './types'

async function get<T>(path: string, params?: Record<string, string>): Promise<T> {
  const query = params ? '?' + new URLSearchParams(params) : ''
  const response = await fetch(`/api${path}${query}`)
  if (!response.ok) {
    const detail = await response.text()
    throw new Error(`${response.status} ${path}: ${detail.slice(0, 200)}`)
  }
  return response.json() as Promise<T>
}

export const api = {
  health: () => get<{ status: string; organizations: number; build_seconds: number | null }>('/health'),
  meta: () => get<Meta>('/meta'),
  overview: () => get<Overview>('/overview'),
  organizations: () => get<Organization[]>('/organizations'),
  organization: (id: string) => get<OrgDetail>(`/organizations/${encodeURIComponent(id)}`),
  clusters: () => get<Clusters>('/clusters'),
  validation: () => get<Validation>('/clusters/validation'),
  recommendations: () => get<{ total: number; items: Recommendation[] }>('/recommendations', { limit: '500' }),
  plan: () => get<PlanRow[]>('/plan'),
  anomalies: () => get<{ total: number; items: Anomaly[] }>('/anomalies'),
  quality: () => get<Quality>('/quality'),
  aiSummary: (refresh = false) =>
    get<AiSummary>('/ai/summary', refresh ? { refresh: 'true' } : undefined),
  aiOrg: (orgId: string, refresh = false) =>
    get<AiSummary>(`/ai/org/${encodeURIComponent(orgId)}`, refresh ? { refresh: 'true' } : undefined),
}
