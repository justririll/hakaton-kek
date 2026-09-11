<script setup>
/**
 * Раздел «Рекомендации по программированию мероприятий»:
 * Симулятор эффекта управленческих решений, каталог 50 мер,
 * фильтрация по типам, важности и центрам.
 */
import { computed, ref } from "vue"
import Icon from "./Icon.vue"
import Disclosure from "./Disclosure.vue"
import { compact, money, getClusterMeta } from "../theme"

const props = defineProps({
  recommendations: { type: Array, required: true },
  summary: { type: Object, required: true },
})

const emit = defineEmits(["select-org"])

// Типы рекомендаций
const KIND = {
  fix_format: { label: "Низкая наполняемость", badgeClass: "badge-accent" },
  expand_format: { label: "Масштабирование формата", badgeClass: "badge-good" },
  launch_format: { label: "Запуск нового формата", badgeClass: "badge-purple" },
  raise_conversion: { label: "Конверсия в арт-продукты", badgeClass: "badge-warning" },
  monetize: { label: "Платная модель и ДПО", badgeClass: "badge-pink" },
  amplify_visibility: { label: "Медийность и PR", badgeClass: "badge-accent" },
  plan_risk: { label: "Риск срыва плана года", badgeClass: "badge-danger" },
}

const IMPACT_WORD = {
  participants: "участников",
  products: "арт-работ",
  revenue: "объёма услуг",
  publications: "публикаций",
  formats: "мероприятий к плану",
}

const activeKind = ref("all")
const onlyImportant = ref(false)
const searchQuery = ref("")

// Параметры симулятора «Что если»
/**
 * Симулятор отвечает на один вопрос: «а если закрыть не весь найденный разрыв,
 * а его часть?». Ползунок — доля разрыва, которую центр реально дотягивает до
 * уровня соседей по архетипу; 100 % означает выход на медиану своей модели.
 *
 * Разрыв дальше медианы не экстраполируется: за пределами наблюдаемого резерва
 * никаких данных нет, и «+50 % сверху» было бы фантазией с точной цифрой.
 */
const simAttendanceShare = ref(100) // % закрытия разрыва по наполняемости
const simConversionShare = ref(100) // % закрытия разрыва по конверсии
const simMonetizeShare = ref(100) // % закрытия разрыва по платным услугам

// Базой служит подтверждённый резерв — без центров с расхождениями в отчёте.
const reserve = computed(() => props.summary?.impact_verified || {})

const simulatedImpact = computed(() => ({
  participants: Math.round((reserve.value.participants?.total || 0) * (simAttendanceShare.value / 100)),
  products: Math.round((reserve.value.products?.total || 0) * (simConversionShare.value / 100)),
  revenue: Math.round((reserve.value.revenue?.total || 0) * (simMonetizeShare.value / 100)),
}))

function resetSim() {
  simAttendanceShare.value = 100
  simConversionShare.value = 100
  simMonetizeShare.value = 100
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
    <!-- Главный вывод -->
    <div class="takeaway-box">
      <div class="takeaway-text">
        <strong>Программирование мероприятий на основе данных:</strong>
        Каждая из <b>{{ summary.total }} рекомендаций</b> сформирована сопоставлением центра с соседями
        по архетипу. Если соседи по кластеру уже собирают больше людей или производят больше
        арт-продуктов в тех же условиях — это наблюдаемый разрыв, а не гипотеза.
        Подтверждённый резерв сети:
        <b>+{{ compact(Math.round(summary.impact_verified?.participants?.total || 0)) }} участников</b>,
        <b>+{{ compact(Math.round(summary.impact_verified?.products?.total || 0)) }} арт-продуктов</b> и
        <b>+{{ money(summary.impact_verified?.revenue?.total) }} выручки</b>
        — без {{ summary.flagged_orgs?.length || 0 }} центров, у которых цифры внутри отчёта
        противоречат друг другу.
      </div>
    </div>

    <!-- Симулятор управленческих решений -->
    <div class="card simulator-card">
      <div class="sim-header">
        <div class="sim-code-tag">СИМУЛЯТОР СЕТИ</div>
        <button class="reset-btn" @click="resetSim">Сбросить параметры</button>
      </div>
      <h2>Какая часть разрыва закрывается</h2>
      <p class="muted sub">
        Ползунок — доля найденного разрыва с соседями по архетипу, которую удаётся закрыть.
        100 % означает выход на медиану своей модели; дальше медианы ничего не достраивается,
        потому что наблюдений за этой границей нет.
      </p>

      <div class="sliders-grid">
        <div class="slider-box">
          <div class="slider-top">
            <span class="slider-label">Наполняемость мероприятий</span>
            <strong class="slider-val">{{ simAttendanceShare }}% разрыва</strong>
          </div>
          <input type="range" min="0" max="100" step="5" v-model.number="simAttendanceShare" />
          <small class="muted">Оптимизация анонсов и запуск повторных потоков</small>
        </div>

        <div class="slider-box">
          <div class="slider-top">
            <span class="slider-label">Конверсия в арт-продукты</span>
            <strong class="slider-val">{{ simConversionShare }}% разрыва</strong>
          </div>
          <input type="range" min="0" max="100" step="5" v-model.number="simConversionShare" />
          <small class="muted">Введение обязательного проектного трека на курсах</small>
        </div>

        <div class="slider-box">
          <div class="slider-top">
            <span class="slider-label">Платные программы и ДПО</span>
            <strong class="slider-val">{{ simMonetizeShare }}% разрыва</strong>
          </div>
          <input type="range" min="0" max="100" step="5" v-model.number="simMonetizeShare" />
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
            placeholder="Поиск по названию центра или действию..."
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
          Все ({{ recommendations.length }})
        </button>
        <button
          v-for="[kind, count] in kinds"
          :key="kind"
          class="chip-btn"
          :class="{ active: activeKind === kind }"
          @click="activeKind = kind"
        >
          <span>{{ KIND[kind]?.label || kind }}</span>
          <span class="chip-count">{{ count }}</span>
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
              {{ KIND[row.rec_type]?.label }}
            </span>
          </div>
          <div class="rec-badges">
            <span
              v-if="row.data_flag"
              class="badge badge-warning"
              title="Контроль качества нашёл расхождение в отчёте этого центра: цифру нужно подтвердить у организации"
            >
              данные под вопросом
            </span>
            <span class="badge" :class="weight(row.priority).class">
              {{ row.priority }} / 100
            </span>
          </div>
        </div>

        <div class="rec-core">
          <div class="rec-action-box">
            <span class="muted action-tag">Действие:</span>
            <h3 class="action-text">{{ row.action }}</h3>
          </div>

          <div class="rec-gain-box">
            <span class="gain-label">Ожидаемый эффект:</span>
            <strong class="gain-value">{{ impactText(row) }}</strong>
          </div>
        </div>

        <p class="rec-rationale muted">
          <b>Обоснование:</b> {{ row.rationale }}
        </p>

        <div class="rec-footer">
          <span class="muted peer-stat">
            Бенчмарк архетипа: <b>{{ row.evidence?.peer_median ?? "—" }}</b> vs текущее: <b>{{ row.evidence?.own_rate ?? "—" }}</b>
          </span>
          <span class="view-dossier-hint">Досье →</span>
        </div>
      </article>

      <div v-if="!filtered.length" class="empty-state card">
        <p class="muted">По заданным критериям рекомендаций не найдено.</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.rec-badges { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; justify-content: flex-end; }

.stack { display: flex; flex-direction: column; gap: 24px; }
.sub { font-size: 13px; margin-top: 2px; }

.simulator-card {
  background: var(--surface);
  border: 1px solid var(--border);
  box-shadow: var(--shadow);
}
.sim-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.sim-code-tag {
  font-size: 11px;
  font-weight: 700;
  font-family: monospace;
  color: var(--accent);
  letter-spacing: 0.05em;
}
.reset-btn { font-size: 12px; padding: 4px 10px; }

.sliders-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 14px;
  margin: 16px 0;
}
.slider-box {
  background: var(--raised);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.slider-top { display: flex; justify-content: space-between; align-items: center; }
.slider-label { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.slider-val { font-size: 13px; color: var(--accent); font-family: monospace; }

.sim-results {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 14px;
  padding-top: 14px;
  border-top: 1px solid var(--border);
}
.res-item {
  background: var(--raised);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.res-value { font-size: 22px; font-weight: 700; color: var(--success); font-variant-numeric: tabular-nums; }
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

.chips-row { display: flex; flex-wrap: wrap; gap: 4px; }
.chip-btn {
  font-size: 12px;
  padding: 5px 11px;
  border-radius: 6px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.chip-count {
  font-size: 11px;
  opacity: 0.7;
  font-family: monospace;
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
  transition: all 0.15s ease;
  border-left: 3px solid var(--accent);
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
  border-radius: 8px;
}
.action-tag { font-size: 11px; text-transform: uppercase; font-weight: 600; }
.action-text { font-size: 13px; font-weight: 600; line-height: 1.45; color: var(--text-primary); }
.rec-gain-box { display: flex; align-items: center; gap: 8px; font-size: 13px; }
.gain-label { color: var(--muted); }
.gain-value { color: var(--success); font-size: 13px; font-weight: 700; }

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
