import { ref } from 'vue'
import { defineStore } from 'pinia'

import { fetchDashboard } from '@/services/analytics'
import type { AnalyticsDashboard } from '@/types/analytics'

export const useAnalyticsStore = defineStore('analytics', () => {
  const dashboard = ref<AnalyticsDashboard | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  async function loadDashboard() {
    isLoading.value = true
    error.value = null

    try {
      dashboard.value = await fetchDashboard()
    } catch (reason) {
      error.value = reason instanceof Error ? reason.message : 'Неизвестная ошибка'
    } finally {
      isLoading.value = false
    }
  }

  return { dashboard, isLoading, error, loadDashboard }
})
