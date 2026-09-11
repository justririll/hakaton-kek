import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useAnalyticsStore } from '../analytics'

describe('analytics store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('loads the dashboard from the API', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ metrics: { total_attendees: 1420 } }),
      }),
    )

    const store = useAnalyticsStore()
    await store.loadDashboard()

    expect(store.dashboard?.metrics.total_attendees).toBe(1420)
    expect(store.error).toBeNull()
    expect(store.isLoading).toBe(false)
  })
})
