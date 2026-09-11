<script setup>
/**
 * Раздел «Рекомендации по программированию мероприятий»:
 * Интерактивный симулятор «Что если», каталог 50 мер,
 * фильтрация по типам, важности и центрам.
 */
import { computed, ref } from "vue"
import Disclosure from "./Disclosure.vue"
import { compact, money, getClusterMeta } from "../theme"

const props = defineProps({
  recommendations: { type: Array, required: true },
  summary: { type: Object, required: true },
})

const emit = defineEmits(["select-org"])

// Типы рекомендаций
const KIND = {
  fix_format: { label: "Мало людей на встречах", icon: "👥", badgeClass: "badge-accent" },
  expand_format: { label: "Формат работает — масштабировать", icon: "↗", badgeClass: "badge-good" },
  launch_format: { label: "Запустить новый формат", icon: "+", badgeClass: "badge-purple" },
  raise_conversion: { label: "Низкая конверсия в продукты", icon: "🎨", badgeClass: "badge-warning" },
  monetize: { label: "Ввести платную модель", icon: "₽", badgeClass: "badge-pink" },
  amplify_visibility: { label: "Слабая медийность (PR)", icon: "📢", badgeClass: "badge-accent" },
  plan_risk: { label: "Риск срыва плана года", icon: "⚠️", badgeClass: "badge-danger" },
}

const IMPACT_WORD = {
  participants: "участников",
  products: "готовых арт-работ",
  revenue: "объёма услуг",
  publications: "публикаций",
  formats: "мероприятий к плану",
}

const activeKind = ref("all")
const onlyImportant = ref(false)
const searchQuery = ref("")

// Параметры интерактивного симулятора «Что если»
const simAttendanceBoost = ref(20) // %
const simConversionBoost = ref(15) // %
const simMonetizeBoost = ref(10) // %

const simulatedImpact = computed(() => {
  const baseParticipants = props.summary?.impact?.participants?.total || 1689
  const baseProducts = props.summary?.impact?.products?.total || 1411
  const baseRevenue = props.summary?.impact?.revenue?.total || 9669800

  const extraParticipants = Math.round(baseParticipants * (simAttendanceBoost.value / 20))
  const extraProducts = Math.round(baseProducts * (simConversionBoost.value / 15))
  const extraRevenue = Math.round(baseRevenue * (simMonetizeBoost.value / 10))

  return {
    participants: extraParticipants,
    products: extraProducts,
    revenue: extraRevenue,
  }
})

function resetSim() {
  simAttendanceBoost.value = 20
  simConversionBoost.value = 15
  simMonetizeBoost.value = 10
}

function weight(priority) {
  if (priority >= 80) return { label: "Высокая важность", level: "high", class: "badge-danger" }
  if (priority >= 50) return { label: "Средняя важность", level: "mid", class: "badge-warning" }
  return { label: "Обычная", level: "low", class: "badge-neutral" }
}

function impactText(row) {
  const val = row.impact_metric === "revenue" ? money(row.impact_value) : compact(row.impact_value)
  const unit = IMPACT_WORD[row.impact_metric] || row.impact_unit || ""
  return `+${val} ${unit}`.trim()
}

const kinds = computed(() => {
  const counts = {}
  for (const r of props.recommendations) counts[r.rec_type] = (counts[r.rec_type] || 0) + 1
  return Object.entries(counts).sort((a, b) => b[1] - a[1])
})

const filtered = computed(() => {
  const q = searchQuery.value.toLowerCase().trim()
  return props.recommendations
    .filter((r) => activeKind.value === "all" || r.rec_type === activeKind.value)
    .filter((r) => !onlyImportant.value || r.priority >= 80)
    .filter((r) => !q || r.org_name.toLowerCase().includes(q) || r.action.toLowerCase().includes(q))
    .sort((a, b) => b.priority - a.priority)
})
</script>

<template>
  <div class="stack">
    <!-- Главный вывод простыми словами -->
    <div class="takeaway-box">
      <span class="takeaway-icon">⚡</span>
      <div class="takeaway-text">
        <strong>Программирование мероприятий на основе данных:</strong>
        Каждая из <b>50 рекомендаций</b> получена сравнением центра только со своими соратниками по архетипу.
        Если соседи по кластеру уже собирают больше людей или делают больше арт-продуктов в тех же условиях —
        это доказанный резерв. Совокупный потенциал сети:
        <b>+{{ compact(summary.impact?.participants?.total) }} участников</b>,
        <b>+{{ compact(summary.impact?.products?.total) }} арт-продуктов</b> и
        <b>+{{ money(summary.impact?.revenue?.total) }} выручки</b>.
      </div>
    </div>

    <!-- Интерактивный симулятор «Что если...» -->
    <div class="card simulator-card">
      <div class="sim-header">
        <div class="sim-badge">
          <span>🎛️</span>
          <span>Интерактивный симулятор программирования сети</span>
        </div>
        <button class="reset-btn" @click="resetSim">Сбросить параметры</button>
      </div>
      <h2>Моделирование эффекта управленческих решений («Что если»)</h2>
      <p class="muted sub">
        Двигайте ползунки, чтобы смоделировать, как корректировка программ мероприятий повлияет на показатели всей сети:
      </p>

      <div class="sliders-grid">
        <div class="slider-box">
          <div class="slider-top">
            <span class="slider-label">👥 Поднять наполняемость мастер-классов</span>
            <strong class="slider-val">+{{ simAttendanceBoost }}%</strong>
          </div>
          <input type="range" min="0" max="50" step="5" v-model.number="simAttendanceBoost" />
          <small class="muted">Оптимизация анонсов и запуск повторных потоков</small>
        </div>

        <div class="slider-box">
          <div class="slider-top">
            <span class="slider-label">🎨 Добавить проектный трек (конверсия)</span>
            <strong class="slider-val">+{{ simConversionBoost }}%</strong>
          </div>
          <input type="range" min="0" max="40" step="5" v-model.number="simConversionBoost" />
          <small class="muted">Введение обязательного творческого прототипа на курсах</small>
        </div>

        <div class="slider-box">
          <div class="slider-top">
            <span class="slider-label">💰 Запустить платные спецкурсы и ДПО</span>
            <strong class="slider-val">+{{ simMonetizeBoost }}%</strong>
          </div>
          <input type="range" min="0" max="60" step="5" v-model.number="simMonetizeBoost" />
          <small class="muted">Платные вечерние слоты и коммерческое прототипирование</small>
        </div>
      </div>

      <!-- Результат симуляции -->
      <div class="sim-results">
        <div class="res-item">
          <span class="res-value">+{{ compact(simulatedImpact.participants) }}</span>
          <span class="res-label">участников обучения</span>
        </div>
        <div class="res-item">
          <span class="res-value">+{{ compact(simulatedImpact.products) }}</span>
          <span class="res-label">готовых арт-продуктов</span>
        </div>
        <div class="res-item">
          <span class="res-value">+{{ money(simulatedImpact.revenue) }}</span>
          <span class="res-label">дополнительного дохода</span>
        </div>
      </div>
    </div>

    <!-- Фильтры и поиск по каталогу рекомендаций -->
    <div class="card search-filter-card">
      <div class="top-filter-row">
        <div class="search-input-wrap">
          <input
            type="search"
            v-model="searchQuery"
            placeholder="Поиск по центру или ключевому слову..."
          />
        </div>
        <div class="important-toggle">
          <label>
            <input type="checkbox" v-model="onlyImportant" />
            <span>Только первоочередные (приоритет ≥ 80)</span>
          </label>
        </div>
      </div>

      <div class="chips-row">
        <button
          class="chip-btn"
          :class="{ active: activeKind === 'all' }"
          @click="activeKind = 'all'"
        >
          Все · {{ recommendations.length }}
        </button>
        <button
          v-for="[kind, count] in kinds"
          :key="kind"
          class="chip-btn"
          :class="{ active: activeKind === kind }"
          @click="activeKind = kind"
        >
          <span>{{ KIND[kind]?.icon }}</span>
          <span>{{ KIND[kind]?.label || kind }}</span>
          <small>· {{ count }}</small>
        </button>
      </div>
    </div>

    <!-- Каталог карточек рекомендаций -->
    <div class="recs-grid">
      <article
        v-for="row in filtered"
        :key="row.rec_id"
        class="card rec-card"
        @click="emit('select-org', row.org_id)"
      >
        <div class="rec-topline">
          <div class="org-info">
            <span class="org-name-btn">{{ row.org_name }}</span>
            <span class="badge" :class="KIND[row.rec_type]?.badgeClass">
              {{ KIND[row.rec_type]?.icon }} {{ KIND[row.rec_type]?.label }}
            </span>
          </div>
          <span class="badge" :class="weight(row.priority).class">
            {{ row.priority }}/100
          </span>
        </div>

        <div class="rec-core">
          <div class="rec-action-box">
            <span class="muted action-tag">Что сделать:</span>
            <h3 class="action-text">{{ row.action }}</h3>
          </div>

          <div class="rec-gain-box">
            <span class="gain-label">Ожидаемый результат:</span>
            <strong class="gain-value">{{ impactText(row) }}</strong>
          </div>
        </div>

        <p class="rec-rationale muted">
          <b>Обоснование:</b> {{ row.rationale }}
        </p>

        <div class="rec-footer">
          <span class="muted peer-stat">
            У соратников по кластеру: <b>{{ row.evidence?.peer_median ?? "—" }}</b> vs текущее: <b>{{ row.evidence?.own_rate ?? "—" }}</b>
          </span>
          <span class="view-dossier-hint">Открыть досье →</span>
        </div>
      </article>

      <div v-if="!filtered.length" class="empty-state card">
        <p class="muted">По заданным фильтрам рекомендаций не найдено.</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.stack { display: flex; flex-direction: column; gap: 24px; }
.sub { font-size: 13px; margin-top: 2px; }

.simulator-card {
  background: linear-gradient(135deg, var(--surface) 0%, var(--raised) 100%);
  border: 1px solid rgba(59, 130, 246, 0.3);
  box-shadow: 0 4px 20px var(--accent-glow);
}
.sim-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.sim-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 700;
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.reset-btn { font-size: 12px; padding: 4px 10px; }

.sliders-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
  margin: 18px 0;
}
.slider-box {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.slider-top { display: flex; justify-content: space-between; align-items: center; }
.slider-label { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.slider-val { font-size: 14px; color: var(--accent); }

.sim-results {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 14px;
  padding-top: 14px;
  border-top: 1px solid var(--border);
}
.res-item {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.res-value { font-size: 22px; font-weight: 700; color: var(--success); }
.res-label { font-size: 12px; color: var(--muted); }

.search-filter-card { display: flex; flex-direction: column; gap: 14px; }
.top-filter-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}
.search-input-wrap { flex: 1; min-width: 260px; }
.search-input-wrap input { width: 100%; }
.important-toggle label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  cursor: pointer;
  color: var(--text-secondary);
}

.chips-row { display: flex; flex-wrap: wrap; gap: 6px; }
.chip-btn {
  font-size: 12px;
  padding: 6px 12px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.recs-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 16px;
}
.rec-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  border-left: 4px solid var(--accent);
}
.rec-card:hover {
  transform: translateY(-2px);
  border-color: var(--accent);
  box-shadow: var(--shadow-lg);
}
.rec-topline { display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; }
.org-info { display: flex; flex-direction: column; gap: 4px; }
.org-name-btn { font-size: 14px; font-weight: 700; color: var(--text-primary); }

.rec-core {
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: var(--raised);
  padding: 12px;
  border-radius: 10px;
}
.action-tag { font-size: 11px; text-transform: uppercase; font-weight: 600; }
.action-text { font-size: 14px; font-weight: 600; line-height: 1.4; color: var(--text-primary); }
.rec-gain-box { display: flex; align-items: center; gap: 8px; font-size: 13px; }
.gain-label { color: var(--muted); }
.gain-value { color: var(--success); font-size: 14px; }

.rec-rationale { font-size: 12px; line-height: 1.5; margin: 0; }
.rec-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
  border-top: 1px solid var(--border);
  padding-top: 8px;
  margin-top: auto;
}
.view-dossier-hint { color: var(--accent); font-weight: 600; }

.empty-state { text-align: center; padding: 40px; grid-column: 1 / -1; }
</style>
