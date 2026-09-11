<script setup>
/** Корневой экран дашборда: загрузка данных и переключение разделов. */
import { onMounted, ref } from 'vue'
import { api } from './api'
import SectionClusters from './components/SectionClusters.vue'
import SectionOverview from './components/SectionOverview.vue'
import SectionQuality from './components/SectionQuality.vue'
import SectionRecommendations from './components/SectionRecommendations.vue'

const SECTIONS = [
  { key: 'overview', label: 'Обзор сети' },
  { key: 'clusters', label: 'Аудиторные модели' },
  { key: 'recommendations', label: 'Рекомендации' },
  { key: 'quality', label: 'Качество данных' },
]

const active = ref('overview')
const loading = ref(true)
const error = ref(null)
const data = ref({})
const theme = ref(document.documentElement.dataset.theme || 'system')

function cycleTheme() {
  const order = ['system', 'light', 'dark']
  theme.value = order[(order.indexOf(theme.value) + 1) % order.length]
  if (theme.value === 'system') delete document.documentElement.dataset.theme
  else document.documentElement.dataset.theme = theme.value
}

onMounted(async () => {
  try {
    const [overview, organizations, plan, clusters, validation, recommendations, anomalies, quality, meta] =
      await Promise.all([
        api.overview(),
        api.organizations(),
        api.plan(),
        api.clusters(),
        api.validation(),
        api.recommendations({ limit: 500 }),
        api.anomalies(),
        api.quality(),
        api.meta(),
      ])
    data.value = {
      overview,
      organizations,
      plan,
      clusters,
      validation,
      recommendations: recommendations.items,
      anomalies: anomalies.items,
      quality,
      meta,
    }
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="shell">
    <header>
      <div class="brand">
        <h1>Культурный пульс</h1>
        <p class="muted">
          Мониторинг сети центров прототипирования и творческих инкубаторов вузов культуры ·
          Формы&nbsp;1 и&nbsp;2, отчётный период 2026&nbsp;года
        </p>
      </div>
      <button class="theme" @click="cycleTheme">
        тема: {{ { system: 'как в системе', light: 'светлая', dark: 'тёмная' }[theme] }}
      </button>
    </header>

    <nav>
      <button
        v-for="section in SECTIONS"
        :key="section.key"
        :class="{ active: active === section.key }"
        @click="active = section.key"
      >
        {{ section.label }}
      </button>
    </nav>

    <main>
      <p v-if="loading" class="state muted">Считаем модели…</p>
      <p v-else-if="error" class="state err">Не удалось загрузить данные: {{ error }}</p>

      <template v-else>
        <SectionOverview
          v-if="active === 'overview'"
          :overview="data.overview"
          :organizations="data.organizations"
          :plan="data.plan"
          :channels="data.meta.channels"
        />
        <SectionClusters
          v-else-if="active === 'clusters'"
          :clusters="data.clusters"
          :validation="data.validation"
        />
        <SectionRecommendations
          v-else-if="active === 'recommendations'"
          :recommendations="data.recommendations"
          :types="data.meta.recommendation_types"
          :summary="data.overview.recommendations"
        />
        <SectionQuality v-else :anomalies="data.anomalies" :quality="data.quality" />
      </template>
    </main>

    <footer class="muted">
      Источник — ежеквартальная отчётность по госпрограмме «Развитие культуры»,
      {{ data.overview?.organizations || '—' }} организаций.
      Модели пересчитаны за {{ data.overview?.build_seconds || '—' }}&nbsp;с.
    </footer>
  </div>
</template>

<style scoped>
.shell { max-width: 1320px; margin: 0 auto; padding: 28px 20px 60px; }
header { display: flex; gap: 20px; align-items: flex-start; justify-content: space-between; flex-wrap: wrap; }
.brand p { font-size: 13px; margin-top: 6px; max-width: 70ch; }
.theme { font-size: 12px; white-space: nowrap; }
nav { display: flex; flex-wrap: wrap; gap: 8px; margin: 24px 0 20px; }
.state { padding: 60px 0; text-align: center; }
.err { color: #d03b3b; }
footer { margin-top: 40px; font-size: 12px; }
</style>
