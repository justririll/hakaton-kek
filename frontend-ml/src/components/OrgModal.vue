<script setup>
import { computed, onMounted, onBeforeUnmount } from "vue"
import Icon from "./Icon.vue"
import EChart from "./EChart.vue"
import { compact, money, percent, PLAN_STATUS, getClusterMeta, palette, baseOption, axisStyle } from "../theme"

const props = defineProps({
  orgId: { type: String, default: null },
  organizations: { type: Array, required: true },
  recommendations: { type: Array, default: () => [] },
  anomalies: { type: Array, default: () => [] },
  clusters: { type: Object, default: () => ({ profiles: [] }) },
  plan: { type: Array, default: () => [] },
  channels: { type: Array, default: () => [] },
})

const emit = defineEmits(["close"])

const org = computed(() => props.organizations.find((o) => o.org_id === props.orgId) || null)
const orgPlan = computed(() => props.plan.find((p) => p.org_id === props.orgId) || null)
const orgRecs = computed(() =>
  props.recommendations.filter((r) => r.org_id === props.orgId).sort((a, b) => b.priority - a.priority),
)
const orgAnomalies = computed(() => props.anomalies.filter((a) => a.org_id === props.orgId))

const clusterMeta = computed(() => {
  if (!org.value) return null
  return getClusterMeta(org.value.cluster)
})

const peers = computed(() => {
  if (!org.value) return []
  return props.organizations.filter((o) => o.cluster === org.value.cluster && o.org_id !== org.value.org_id)
})

/** График структуры форматов для организации */
const formatChartOption = computed(() => {
  if (!org.value || !props.channels.length) return {}
  const p = palette()
  const data = props.channels.map((ch, idx) => ({
    name: ch.label,
    value: org.value[`audience_${ch.key}`] || 0,
    itemStyle: { color: p.series[idx % p.series.length] },
  }))

  return {
    ...baseOption(),
    tooltip: { trigger: "item", formatter: "{b}: <b>{c} чел.</b> ({d}%)" },
    legend: { bottom: 0, left: "center", textStyle: { color: p.textSecondary, fontSize: 11 } },
    series: [
      {
        name: "Форматы",
        type: "pie",
        radius: ["45%", "70%"],
        center: ["50%", "42%"],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 6, borderColor: p.surface, borderWidth: 2 },
        label: { show: false },
        emphasis: { label: { show: true, fontSize: 12, fontWeight: "bold" } },
        data,
      },
    ],
  }
})

function onKeydown(e) {
  if (e.key === "Escape") emit("close")
}

onMounted(() => window.addEventListener("keydown", onKeydown))
onBeforeUnmount(() => window.removeEventListener("keydown", onKeydown))
</script>

<template>
  <div v-if="org" class="modal-overlay" @click.self="emit('close')">
    <div class="modal-container">
      <div class="modal-header">
        <div class="header-left">
          <div class="cluster-badge" :style="{ backgroundColor: clusterMeta?.glow, color: clusterMeta?.color }">
            <span class="cluster-code">{{ clusterMeta?.code }}</span>
            <span>{{ clusterMeta?.name }}</span>
          </div>
          <h2>{{ org.short_name }}</h2>
          <p class="muted org-fullname">{{ org.full_name }}</p>
        </div>
        <button class="close-btn" @click="emit('close')" title="Закрыть">
          <Icon name="x" :size="16" />
        </button>
      </div>

      <div class="modal-body">
        <!-- Ключевые показатели организации -->
        <div class="stats-grid">
          <div class="stat-card">
            <span class="label">Посещаемость</span>
            <strong class="value">{{ compact(org.audience_total) }}</strong>
            <small class="muted">человек обучено</small>
          </div>
          <div class="stat-card">
            <span class="label">Проведено форматов</span>
            <strong class="value">{{ compact(org.supply_total) }}</strong>
            <small class="muted">{{ org.audience_per_format?.toFixed(1) }} чел./событие</small>
          </div>
          <div class="stat-card">
            <span class="label">Арт-продуктов</span>
            <strong class="value">{{ compact(org.products_total) }}</strong>
            <small class="muted">{{ org.product_rate?.toFixed(2) }} работ/чел.</small>
          </div>
          <div class="stat-card">
            <span class="label">Выручка от услуг</span>
            <strong class="value">{{ money(org.revenue_total) }}</strong>
            <small class="muted">{{ money(org.revenue_per_participant) }}/участник</small>
          </div>
        </div>

        <!-- Исполнение плана и статус -->
        <div v-if="orgPlan" class="plan-card">
          <div class="plan-top">
            <div>
              <h3>Исполнение годового плана госпрограммы</h3>
              <p class="muted">
                Цель 2026: <b>{{ orgPlan.target_2026 }} ед.</b> • Факт 9 мес: <b>{{ orgPlan.fact_ytd }} ед.</b>
              </p>
            </div>
            <span
              class="badge"
              :class="{
                'badge-good': orgPlan.status === 'опережение' || orgPlan.status === 'в графике',
                'badge-warning': orgPlan.status === 'риск',
                'badge-danger': orgPlan.status === 'срыв',
                'badge-neutral': orgPlan.status === 'без базы',
              }"
            >
              {{ orgPlan.status }}
            </span>
          </div>

          <div class="progress-track">
            <div
              class="progress-fill"
              :style="{
                width: `${Math.min(100, Math.round(orgPlan.completion * 100))}%`,
                backgroundColor: PLAN_STATUS[orgPlan.status]?.color || 'var(--accent)',
              }"
            />
          </div>
          <div class="plan-meta">
            <span>Выполнено: <b>{{ percent(orgPlan.completion) }}</b></span>
            <span>Прогноз года: <b>{{ orgPlan.run_rate_forecast }} ед.</b></span>
            <span>Требуется в IV кв.: <b>{{ orgPlan.required_remaining }} ед.</b> ({{ orgPlan.required_monthly_rate }} в мес.)</span>
          </div>
        </div>

        <!-- Две колонки: форматы и соратники по кластеру -->
        <div class="two-cols">
          <div class="card mini-card">
            <h4>Структура аудитории по форматам</h4>
            <EChart :option="formatChartOption" height="220px" />
          </div>

          <div class="card mini-card">
            <h4>Соседи по модели «{{ clusterMeta?.name }}»</h4>
            <p class="muted sub-text">С ними центр сопоставляется при расчёте резервов:</p>
            <div class="peers-list">
              <div v-for="peer in peers" :key="peer.org_id" class="peer-row">
                <span class="peer-name">{{ peer.short_name }}</span>
                <span class="peer-stat">{{ compact(peer.audience_total) }} чел.</span>
              </div>
              <p v-if="!peers.length" class="muted">В данном архетипе нет других центров</p>
            </div>
          </div>
        </div>

        <!-- Персональные рекомендации для центра -->
        <div class="recommendations-section">
          <h3>Рекомендации по программированию мероприятий ({{ orgRecs.length }})</h3>
          <p class="muted">Меры, рассчитанные на основе практик лучших центров того же архетипа:</p>

          <div class="rec-list">
            <div v-for="rec in orgRecs" :key="rec.rec_id" class="rec-item">
              <div class="rec-top">
                <span class="badge badge-accent">Приоритет {{ rec.priority }}/100</span>
                <strong class="rec-impact">
                  +{{ rec.impact_metric === 'revenue' ? money(rec.impact_value) : compact(rec.impact_value) }}
                  {{ rec.impact_unit }}
                </strong>
              </div>
              <p class="rec-action"><b>Действие:</b> {{ rec.action }}</p>
              <p class="rec-rationale muted"><b>Обоснование:</b> {{ rec.rationale }}</p>
            </div>
            <p v-if="!orgRecs.length" class="muted">Для данного центра нет критических отклонений от нормы архетипа.</p>
          </div>
        </div>

        <!-- Аномалии отчётности (если есть) -->
        <div v-if="orgAnomalies.length" class="anomalies-section">
          <h4 class="text-danger">Обнаруженные расхождения в отчёте ({{ orgAnomalies.length }})</h4>
          <div v-for="(anom, i) in orgAnomalies" :key="i" class="anomaly-item">
            <span class="badge badge-danger">Внимание</span>
            <span>{{ anom.description || anom.message }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.header-left { display: flex; flex-direction: column; gap: 6px; }
.org-fullname { font-size: 13px; max-width: 680px; }
.cluster-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 6px;
  width: fit-content;
}
.cluster-code { font-family: monospace; }

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
}
.stat-card {
  background: var(--raised);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.stat-card .label { font-size: 11px; color: var(--muted); text-transform: uppercase; }
.stat-card .value { font-size: 20px; font-weight: 700; color: var(--text-primary); font-variant-numeric: tabular-nums; }

.plan-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.plan-top { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
.progress-track {
  height: 6px;
  background: var(--raised);
  border-radius: 999px;
  overflow: hidden;
}
.progress-fill { height: 100%; border-radius: 999px; transition: width 0.3s ease; }
.plan-meta {
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
  font-size: 12px;
  color: var(--text-secondary);
}

.two-cols {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
@media (max-width: 680px) {
  .two-cols { grid-template-columns: 1fr; }
}
.mini-card { padding: 16px; }
.sub-text { font-size: 12px; margin: 4px 0 10px; }
.peers-list { display: flex; flex-direction: column; gap: 6px; max-height: 180px; overflow-y: auto; }
.peer-row {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  padding: 6px 10px;
  background: var(--raised);
  border-radius: 6px;
}

.recommendations-section { display: flex; flex-direction: column; gap: 10px; }
.rec-list { display: flex; flex-direction: column; gap: 10px; }
.rec-item {
  background: var(--surface);
  border: 1px solid var(--border);
  border-left: 3px solid var(--accent);
  border-radius: 8px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.rec-top { display: flex; justify-content: space-between; align-items: center; }
.rec-impact { color: var(--success); font-weight: 600; font-size: 13px; font-variant-numeric: tabular-nums; }
.rec-action { font-size: 13px; color: var(--text-primary); }
.rec-rationale { font-size: 12px; }

.anomalies-section {
  background: var(--danger-wash);
  border: 1px solid rgba(239, 68, 68, 0.25);
  border-radius: 10px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.text-danger { color: var(--danger); font-size: 13px; }
.anomaly-item { display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--text-primary); }
</style>
