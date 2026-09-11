<script setup>
/** Корневой экран дашборда: загрузка данных и переключение разделов. */
import { onMounted, ref } from 'vue'
import { api } from './api'
import SectionClusters from './components/SectionClusters.vue'
import SectionOverview from './components/SectionOverview.vue'
import SectionQuality from './components/SectionQuality.vue'
import SectionRecommendations from './components/SectionRecommendations.vue'
import SectionStory from './components/SectionStory.vue'

const SECTIONS = [
  { key: 'story', label: 'Главное' },
  { key: 'clusters', label: 'Типы центров' },
  { key: 'recommendations', label: 'Что делать' },
  { key: 'overview', label: 'Показатели' },
  { key: 'quality', label: 'Качество данных' },
]

const active = ref('story')
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
        <span class="mark">КП</span>
        <div>
          <h1>Культурный пульс</h1>
          <p class="muted">Аналитика сети центров культуры</p>
        </div>
      </div>
      <button class="theme" @click="cycleTheme">
        {{ { system: '◐ как в системе', light: '☀ светлая', dark: '☾ тёмная' }[theme] }}
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
        <SectionStory
          v-if="active === 'story'"
          :overview="data.overview"
          :recommendations="data.recommendations"
          :anomalies="data.anomalies"
          :clusters="data.clusters"
          :validation="data.validation"
        />
        <SectionClusters
          v-else-if="active === 'clusters'"
          :clusters="data.clusters"
          :validation="data.validation"
          :organizations="data.organizations"
        />
        <SectionRecommendations
          v-else-if="active === 'recommendations'"
          :recommendations="data.recommendations"
          :summary="data.overview.recommendations"
        />
        <SectionOverview
          v-else-if="active === 'overview'"
          :overview="data.overview"
          :organizations="data.organizations"
          :plan="data.plan"
          :channels="data.meta.channels"
        />
        <SectionQuality v-else :anomalies="data.anomalies" :quality="data.quality" />
      </template>
    </main>

    <footer class="muted">
      Источник — ежеквартальная отчётность по госпрограмме «Развитие культуры»,
      {{ data.overview?.organizations || '—' }} организаций. Все модели пересчитываются
      за {{ data.overview?.build_seconds || '—' }}&nbsp;с.
    </footer>
  </div>
</template>

<style scoped>
.shell { max-width: 1240px; margin: 0 auto; padding: 24px 20px 60px; }

header { display: flex; gap: 20px; align-items: center; justify-content: space-between; flex-wrap: wrap; }
.brand { display: flex; gap: 12px; align-items: center; }
.mark {
  width: 38px;
  height: 38px;
  border-radius: 11px;
  background: var(--accent);
  color: #fff;
  display: grid;
  place-items: center;
  font-weight: 700;
  font-size: 14px;
  letter-spacing: -0.02em;
}
.brand p { font-size: 12px; margin-top: 1px; }
.theme { font-size: 12px; white-space: nowrap; }

nav {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin: 26px 0 22px;
  padding: 4px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  width: fit-content;
  max-width: 100%;
}
nav button { border: none; border-radius: 8px; font-size: 13px; padding: 7px 14px; }

.state { padding: 70px 0; text-align: center; }
.err { color: #d03b3b; }
footer { margin-top: 44px; font-size: 12px; }
</style>
