<script setup>
/**
 * Корневой экран платформы «Культурный пульс»:
 * Навигация по 7 ключевым разделам, быстрый выбор центров,
 * экспресс-отчет для руководства и переключение тем.
 */
import { onMounted, ref } from "vue"
import { api } from "./api"
import SectionStory from "./components/SectionStory.vue"
import SectionDynamics from "./components/SectionDynamics.vue"
import SectionFeedback from "./components/SectionFeedback.vue"
import SectionClusters from "./components/SectionClusters.vue"
import SectionRecommendations from "./components/SectionRecommendations.vue"
import SectionOrganizations from "./components/SectionOrganizations.vue"
import SectionQuality from "./components/SectionQuality.vue"
import OrgModal from "./components/OrgModal.vue"
import ExecutiveSummaryModal from "./components/ExecutiveSummaryModal.vue"

const SECTIONS = [
  { key: "story", label: "Главное & Пульс", icon: "🌟" },
  { key: "dynamics", label: "Посещаемость & Динамика", icon: "📈" },
  { key: "feedback", label: "Обратная связь & Вовлеченность", icon: "💬" },
  { key: "clusters", label: "Кластеризация аудитории", icon: "🎭" },
  { key: "recommendations", label: "Рекомендации & Симулятор", icon: "⚡" },
  { key: "organizations", label: "Центры культуры (20)", icon: "🏛️" },
  { key: "quality", label: "Контроль качества", icon: "🛡️" },
]

const active = ref("story")
const loading = ref(true)
const error = ref(null)
const data = ref({})
const theme = ref(document.documentElement.dataset.theme || "system")

// Модальные окна
const selectedOrgId = ref(null)
const showSummaryModal = ref(false)

function cycleTheme() {
  const order = ["system", "light", "dark"]
  theme.value = order[(order.indexOf(theme.value) + 1) % order.length]
  if (theme.value === "system") delete document.documentElement.dataset.theme
  else document.documentElement.dataset.theme = theme.value
}

function openOrg(orgId) {
  selectedOrgId.value = orgId
}

function switchTab(tabKey) {
  active.value = tabKey
  window.scrollTo({ top: 0, behavior: "smooth" })
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
    <!-- Шапка платформы -->
    <header class="app-header">
      <div class="brand-block">
        <div class="brand-logo">КП</div>
        <div>
          <div class="title-row">
            <h1>Культурный пульс</h1>
            <span class="live-status">
              <span class="pulse-indicator" />
              <span>20 центров сети онлайн</span>
            </span>
          </div>
          <p class="muted subtitle">Интеллектуальная аналитика и программирование мероприятий</p>
        </div>
      </div>

      <div class="header-actions">
        <!-- Быстрый выбор центра для перехода в досье -->
        <div v-if="data.organizations?.length" class="quick-org-selector">
          <select @change="(e) => { if (e.target.value) { openOrg(e.target.value); e.target.value = ''; } }">
            <option value="">Быстрый поиск центра...</option>
            <option v-for="org in data.organizations" :key="org.org_id" :value="org.org_id">
              {{ org.short_name }}
            </option>
          </select>
        </div>

        <!-- Экспресс-отчет для руководства / жюри -->
        <button
          v-if="!loading && !error"
          class="btn-report"
          @click="showSummaryModal = true"
        >
          📄 Экспресс-отчёт
        </button>

        <!-- Переключатель темы -->
        <button class="theme-btn" @click="cycleTheme" title="Сменить тему оформления">
          {{ { system: "◐ Система", light: "☀ Светлая", dark: "☾ Тёмная" }[theme] }}
        </button>
      </div>
    </header>

    <!-- Горизонтальная навигация по 7 разделам -->
    <nav class="main-nav">
      <button
        v-for="section in SECTIONS"
        :key="section.key"
        :class="{ active: active === section.key }"
        class="nav-tab"
        @click="active = section.key"
      >
        <span class="tab-icon">{{ section.icon }}</span>
        <span>{{ section.label }}</span>
      </button>
    </nav>

    <!-- Основной контент -->
    <main>
      <div v-if="loading" class="state-box">
        <div class="spinner" />
        <p class="muted">Анализируем данные 20 учреждений культуры и строим модели…</p>
      </div>

      <div v-else-if="error" class="state-box err-box">
        <p class="err-title">Не удалось загрузить аналитические модели</p>
        <p class="muted">{{ error }}</p>
        <button class="btn-primary" style="margin-top: 12px;" @click="window.location.reload()">Повторить</button>
      </div>

      <template v-else>
        <!-- 1. Главное & Пульс -->
        <SectionStory
          v-if="active === 'story'"
          :overview="data.overview"
          :recommendations="data.recommendations"
          :anomalies="data.anomalies"
          :clusters="data.clusters"
          :validation="data.validation"
          @select-tab="switchTab"
          @select-org="openOrg"
        />

        <!-- 2. Посещаемость & Динамика -->
        <SectionDynamics
          v-else-if="active === 'dynamics'"
          :overview="data.overview"
          :organizations="data.organizations"
          :plan="data.plan"
          :channels="data.meta.channels"
          @select-org="openOrg"
        />

        <!-- 3. Обратная связь & Вовлеченность -->
        <SectionFeedback
          v-else-if="active === 'feedback'"
          :overview="data.overview"
          :organizations="data.organizations"
        />

        <!-- 4. Кластеризация аудитории -->
        <SectionClusters
          v-else-if="active === 'clusters'"
          :clusters="data.clusters"
          :validation="data.validation"
          :organizations="data.organizations"
          @select-org="openOrg"
        />

        <!-- 5. Рекомендации & Симулятор -->
        <SectionRecommendations
          v-else-if="active === 'recommendations'"
          :recommendations="data.recommendations"
          :summary="data.overview.recommendations"
          @select-org="openOrg"
        />

        <!-- 6. Центры культуры (Каталог 20 организаций) -->
        <SectionOrganizations
          v-else-if="active === 'organizations'"
          :organizations="data.organizations"
          :plan="data.plan"
          :clusters="data.clusters"
          @select-org="openOrg"
        />

        <!-- 7. Контроль качества данных -->
        <SectionQuality
          v-else-if="active === 'quality'"
          :anomalies="data.anomalies"
          :quality="data.quality"
        />
      </template>
    </main>

    <!-- Подвал -->
    <footer class="app-footer">
      <div class="footer-content muted">
        <div>
          Источник: ежеквартальная отчётность по госпрограмме «Развитие культуры» (Формы 1 и 2).
          Охват: {{ data.overview?.organizations || 20 }} организаций.
        </div>
        <div>
          Полный аналитический конвейер пересчитан за {{ data.overview?.build_seconds || "—" }}&nbsp;с.
        </div>
      </div>
    </footer>

    <!-- Модальное окно досье организации -->
    <OrgModal
      v-if="selectedOrgId"
      :orgId="selectedOrgId"
      :organizations="data.organizations || []"
      :recommendations="data.recommendations || []"
      :anomalies="data.anomalies || []"
      :clusters="data.clusters || { profiles: [] }"
      :plan="data.plan || []"
      :channels="data.meta?.channels || []"
      @close="selectedOrgId = null"
    />

    <!-- Модальное окно экспресс-отчёта для руководства -->
    <ExecutiveSummaryModal
      v-if="showSummaryModal"
      :overview="data.overview"
      :clusters="data.clusters"
      :plan="data.plan"
      @close="showSummaryModal = false"
    />
  </div>
</template>

<style scoped>
.shell {
  max-width: 1280px;
  margin: 0 auto;
  padding: 24px 20px 80px;
}

.app-header {
  display: flex;
  gap: 20px;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--border);
}
.brand-block { display: flex; gap: 14px; align-items: center; }
.brand-logo {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: linear-gradient(135deg, var(--accent) 0%, #1d4ed8 100%);
  color: #ffffff;
  display: grid;
  place-items: center;
  font-weight: 800;
  font-size: 16px;
  letter-spacing: -0.02em;
  box-shadow: 0 4px 12px var(--accent-glow);
}
.title-row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.title-row h1 { font-size: 20px; font-weight: 700; }
.live-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 600;
  color: var(--success);
  background: var(--success-wash);
  padding: 2px 8px;
  border-radius: 999px;
}
.subtitle { font-size: 12px; margin-top: 2px; }

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.quick-org-selector select {
  font-size: 13px;
  padding: 6px 12px;
  min-width: 220px;
}
.btn-report {
  background: var(--accent-wash);
  color: var(--accent);
  border: 1px solid rgba(59, 130, 246, 0.3);
  font-weight: 600;
  font-size: 13px;
}
.btn-report:hover {
  background: var(--accent);
  color: #ffffff;
}
.theme-btn { font-size: 12px; white-space: nowrap; }

.main-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 22px 0 26px;
  padding: 6px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  box-shadow: var(--shadow-sm);
  overflow-x: auto;
}
.nav-tab {
  border: 1px solid transparent;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  padding: 8px 14px;
  color: var(--text-secondary);
  white-space: nowrap;
}
.nav-tab:hover {
  color: var(--text-primary);
  background: var(--raised);
}
.nav-tab.active {
  background: var(--accent);
  color: #ffffff;
  border-color: var(--accent);
  box-shadow: 0 2px 10px var(--accent-glow);
}
.tab-icon { font-size: 15px; }

.state-box {
  padding: 90px 20px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}
.spinner {
  width: 36px;
  height: 36px;
  border: 3px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
.err-box { color: var(--danger); }
.err-title { font-size: 16px; font-weight: 700; }

.app-footer {
  margin-top: 50px;
  padding-top: 20px;
  border-top: 1px solid var(--border);
  font-size: 12px;
}
.footer-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}
</style>
