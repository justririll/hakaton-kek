<script setup>
/**
 * Корневой экран платформы «Культурный пульс»:
 * Навигация по разделам, быстрый выбор центров,
 * экспресс-отчет для руководства и переключение тем.
 */
import { onMounted, ref, computed } from "vue"
import { api } from "./api"
import Icon from "./components/Icon.vue"
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
  { key: "story", label: "Главное", icon: "activity" },
  { key: "dynamics", label: "Динамика", icon: "trending-up" },
  { key: "feedback", label: "Обратная связь", icon: "message-square" },
  { key: "clusters", label: "Модели аудитории", icon: "layers" },
  { key: "recommendations", label: "Рекомендации", icon: "zap" },
  { key: "organizations", label: "Каталог центров", icon: "building" },
  { key: "quality", label: "Качество данных", icon: "shield-check" },
]

const active = ref("story")
const loading = ref(true)
const error = ref(null)
const data = ref({})
const theme = ref(document.documentElement.dataset.theme || "system")

const activeSectionIndex = computed(() => SECTIONS.findIndex((s) => s.key === active.value))
const currentSection = computed(() => SECTIONS[activeSectionIndex.value] || SECTIONS[0])

function prevSection() {
  if (activeSectionIndex.value > 0) {
    active.value = SECTIONS[activeSectionIndex.value - 1].key
    window.scrollTo({ top: 0, behavior: "smooth" })
  }
}

function nextSection() {
  if (activeSectionIndex.value < SECTIONS.length - 1) {
    active.value = SECTIONS[activeSectionIndex.value + 1].key
    window.scrollTo({ top: 0, behavior: "smooth" })
  }
}

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
        <div class="brand-logo">
          <Icon name="activity" :size="20" />
        </div>
        <div>
          <div class="title-row">
            <h1>Культурный пульс</h1>
            <span class="live-status">
              <span class="pulse-indicator" />
              <span>20 центров онлайн</span>
            </span>
          </div>
          <p class="muted subtitle">Аналитика сети центров прототипирования и программирование мероприятий</p>
        </div>
      </div>

      <div class="header-actions">
        <!-- Быстрый выбор центра для перехода в досье -->
        <div v-if="data.organizations?.length" class="quick-org-selector">
          <Icon name="search" :size="14" class="search-icon-inside" />
          <select @change="(e) => { if (e.target.value) { openOrg(e.target.value); e.target.value = ''; } }">
            <option value="">Найти центр...</option>
            <option v-for="org in data.organizations" :key="org.org_id" :value="org.org_id">
              {{ org.short_name }}
            </option>
          </select>
        </div>

        <!-- Экспресс-отчет для руководства -->
        <button
          v-if="!loading && !error"
          class="btn-report"
          @click="showSummaryModal = true"
        >
          <Icon name="file-text" :size="14" />
          <span>Экспресс-отчёт</span>
        </button>

        <!-- Переключатель темы -->
        <button class="theme-btn" @click="cycleTheme" title="Сменить тему оформления">
          <Icon :name="theme === 'dark' ? 'moon' : 'sun'" :size="14" />
          <span>{{ { system: "Авто", light: "Светлая", dark: "Тёмная" }[theme] }}</span>
        </button>
      </div>
    </header>

    <!-- Десктопная горизонтальная навигация по 7 разделам (на экранах > 860px) -->
    <nav class="main-nav desktop-nav">
      <button
        v-for="section in SECTIONS"
        :key="section.key"
        :class="{ active: active === section.key }"
        class="nav-tab"
        @click="active = section.key"
      >
        <Icon :name="section.icon" :size="15" />
        <span>{{ section.label }}</span>
      </button>
    </nav>

    <!-- Мобильный селектор разделов (на экранах <= 860px) - без необходимости листать вкладки! -->
    <nav class="mobile-nav-bar">
      <button
        class="mobile-nav-arrow"
        :disabled="activeSectionIndex <= 0"
        @click="prevSection"
        title="Предыдущий раздел"
      >
        <Icon name="chevron-left" :size="16" />
      </button>

      <div class="mobile-nav-dropdown">
        <Icon :name="currentSection.icon" :size="16" class="dropdown-icon" />
        <select v-model="active" class="mobile-section-select">
          <option
            v-for="(section, idx) in SECTIONS"
            :key="section.key"
            :value="section.key"
          >
            {{ idx + 1 }}. {{ section.label }}
          </option>
        </select>
        <div class="dropdown-display">
          <span class="dropdown-label">{{ currentSection.label }}</span>
          <span class="dropdown-counter">{{ activeSectionIndex + 1 }}/{{ SECTIONS.length }}</span>
        </div>
        <Icon name="chevron-down" :size="14" class="dropdown-chevron" />
      </div>

      <button
        class="mobile-nav-arrow"
        :disabled="activeSectionIndex >= SECTIONS.length - 1"
        @click="nextSection"
        title="Следующий раздел"
      >
        <Icon name="chevron-right" :size="16" />
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

      <Transition v-else name="section" mode="out-in">
        <div :key="active" class="section-wrap">
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
        </div>
      </Transition>
    </main>

    <!-- Подвал -->
    <footer class="app-footer">
      <div class="footer-content muted">
        <div>
          Источник: ежеквартальная ведомственная отчётность (Формы 1 и 2).
          Охват: {{ data.overview?.organizations || 20 }} организаций.
        </div>
        <div>
          Пересчёт конвейера моделей: {{ data.overview?.build_seconds || "—" }}&nbsp;с.
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
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: var(--accent);
  color: #ffffff;
  display: grid;
  place-items: center;
  box-shadow: 0 2px 10px var(--accent-glow);
}
.title-row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.title-row h1 { font-size: 20px; font-weight: 700; letter-spacing: -0.02em; }
.live-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 600;
  color: var(--success);
  background: var(--success-wash);
  padding: 3px 8px;
  border-radius: 999px;
}
.subtitle { font-size: 12px; margin-top: 2px; }

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.quick-org-selector {
  position: relative;
  display: flex;
  align-items: center;
}
.search-icon-inside {
  position: absolute;
  left: 10px;
  color: var(--muted);
  pointer-events: none;
}
.quick-org-selector select {
  font-size: 13px;
  padding: 7px 12px 7px 30px;
  min-width: 220px;
}
.btn-report {
  background: var(--accent-wash);
  color: var(--accent);
  border: 1px solid rgba(59, 130, 246, 0.25);
  font-weight: 600;
  font-size: 13px;
  gap: 6px;
}
.btn-report:hover {
  background: var(--accent);
  color: #ffffff;
}
.theme-btn { font-size: 12px; white-space: nowrap; gap: 6px; }

.main-nav {
  display: flex;
  flex-wrap: nowrap;
  gap: 6px;
  margin: 20px 0 24px;
  padding: 5px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: var(--shadow-sm);
  overflow-x: auto;
  scrollbar-width: none;
  -ms-overflow-style: none;
}
.main-nav::-webkit-scrollbar {
  display: none;
}
.nav-tab {
  flex: 1;
  display: inline-flex;
  justify-content: center;
  align-items: center;
  border: 1px solid transparent;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  padding: 8px 10px;
  color: var(--text-secondary);
  white-space: nowrap;
  flex-shrink: 0;
  gap: 7px;
  transition: all 0.15s ease;
}
.nav-tab:hover {
  color: var(--text-primary);
  background: var(--raised);
}
.nav-tab.active {
  background: var(--accent);
  color: #ffffff;
  border-color: var(--accent);
  box-shadow: 0 2px 8px var(--accent-glow);
}

.state-box {
  padding: 90px 20px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}
.spinner {
  width: 34px;
  height: 34px;
  border: 3px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
/* Переключение разделов: короткий сдвиг вверх вместо мгновенной подмены.
   mode="out-in" не даёт двум разделам накладываться друг на друга. */
.section-enter-active,
.section-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}
.section-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.section-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

/* Пользователям, попросившим убрать анимации, отдаём мгновенную подмену. */
@media (prefers-reduced-motion: reduce) {
  .section-enter-active,
  .section-leave-active {
    transition: none;
  }
  .section-enter-from,
  .section-leave-to {
    opacity: 1;
    transform: none;
  }
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

.mobile-nav-bar {
  display: none;
}

@media (max-width: 860px) {
  .shell {
    padding: 12px 12px 60px;
  }
  .app-header {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
    padding-bottom: 14px;
  }
  .header-actions {
    display: flex;
    width: 100%;
    justify-content: space-between;
    gap: 6px;
  }
  .quick-org-selector {
    flex: 1;
    min-width: 0;
  }
  .quick-org-selector select {
    width: 100%;
    min-width: 0;
    font-size: 12px;
  }
  .btn-report {
    padding: 6px 10px;
    font-size: 12px;
  }
  .theme-btn {
    padding: 6px 10px;
    font-size: 12px;
  }
  .desktop-nav {
    display: none !important;
  }
  .mobile-nav-bar {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 12px 0 18px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 6px;
    box-shadow: var(--shadow-sm);
  }
  .mobile-nav-arrow {
    width: 38px;
    height: 38px;
    border-radius: 8px;
    background: var(--raised);
    border: 1px solid var(--border);
    display: grid;
    place-items: center;
    color: var(--text-primary);
    flex-shrink: 0;
    cursor: pointer;
    transition: all 0.15s ease;
  }
  .mobile-nav-arrow:disabled {
    opacity: 0.3;
    cursor: not-allowed;
  }
  .mobile-nav-arrow:not(:disabled):active {
    background: var(--accent);
    color: #ffffff;
  }
  .mobile-nav-dropdown {
    position: relative;
    flex: 1;
    display: flex;
    align-items: center;
    background: var(--raised);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0 12px;
    height: 38px;
    gap: 8px;
    cursor: pointer;
  }
  .dropdown-icon {
    color: var(--accent);
    flex-shrink: 0;
  }
  .dropdown-display {
    flex: 1;
    display: flex;
    justify-content: space-between;
    align-items: center;
    min-width: 0;
  }
  .dropdown-label {
    font-size: 13px;
    font-weight: 700;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .dropdown-counter {
    font-size: 11px;
    font-weight: 600;
    color: var(--muted);
    background: var(--surface);
    padding: 2px 6px;
    border-radius: 4px;
    margin-left: 6px;
    flex-shrink: 0;
  }
  .dropdown-chevron {
    color: var(--muted);
    flex-shrink: 0;
  }
  .mobile-section-select {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    width: 100%;
    height: 100%;
    opacity: 0;
    cursor: pointer;
    -webkit-appearance: menulist-button;
  }
}
</style>
