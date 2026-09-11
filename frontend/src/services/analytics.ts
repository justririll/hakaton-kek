import type { AnalyticsDashboard } from '@/types/analytics'

const DASHBOARD_URL = '/api/v1/analytics/dashboard'

export async function fetchDashboard(): Promise<AnalyticsDashboard> {
  const response = await fetch(DASHBOARD_URL, {
    headers: { Accept: 'application/json' },
  })

  if (!response.ok) {
    throw new Error(`API вернул ошибку ${response.status}`)
  }

  return response.json() as Promise<AnalyticsDashboard>
}
