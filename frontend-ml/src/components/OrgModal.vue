<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from "vue"
import { api } from "../api"
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
    legend: {
      bottom: 0,
      left: "center",
      itemWidth: 8,
      itemHeight: 8,
      itemGap: 8,
      textStyle: { color: p.textSecondary, fontSize: 10 },
    },
    series: [
      {
        name: "Форматы",
        type: "pie",
        radius: ["36%", "56%"],
        center: ["50%", "36%"],
        avoidLabelOverlap: true,
        itemStyle: { borderRadius: 4, borderColor: p.surface, borderWidth: 2 },
        label: { show: false },
        emphasis: { label: { show: false } },
        data,
      },
    ],
  }
})

// Gemini AI персональный разбор центра
const aiLoading = ref(false)
const aiResult = ref(null)
const aiError = ref(null)

async function loadAiOrg(force = false) {
  if (!props.orgId) return
  aiLoading.value = true
  aiError.value = null
  try {
    const res = await api.aiOrgSummary(props.orgId, force)
    aiResult.value = res
  } catch (e) {
    aiError.value = e.message || "Ошибка генерации AI-разбора"
  } finally {
    aiLoading.value = false
  }
}

const aiSections = computed(() => {
  if (!aiResult.value?.content) return []
  const text = aiResult.value.content
  const rawSections = text.split(/###\s+/).filter(Boolean)
  if (rawSections.length === 0 || !text.includes("###")) {
    return [{
      title: "Аналитический разбор",
      paragraphs: text.split("\n\n").filter(Boolean),
      items: [],
    }]
  }
  return rawSections.map((sec) => {
    const lines = sec.trim().split("\n")
    const title = lines[0].replace(/^[\d.]+\s*/, "").trim()
    const rest = lines.slice(1).join("\n").trim()
    const items = []
    const paras = []
    for (const line of rest.split("\n")) {
      const trimmed = line.trim()
      if (!trimmed || trimmed === "---") continue
      if (trimmed.startsWith("-") || trimmed.startsWith("*") || /^\d+\./.test(trimmed)) {
        items.push(trimmed.replace(/^[-*]\s+|\d+\.\s*/, ""))
      } else {
        paras.push(trimmed)
      }
    }
    return { title, paragraphs: paras, items }
  })
})

function formatBold(str) {
  if (!str) return ""
  return str
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/g, "<em>$1</em>")
    .replace(/`(.*?)`/g, "<code>$1</code>")
}

function onKeydown(e) {
  if (e.key === "Escape") emit("close")
}

onMounted(() => {
  window.addEventListener("keydown", onKeydown)
  loadAiOrg(false)
})
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
            <EChart :option="formatChartOption" height="240px" />
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

        <!-- Персональный AI-разбор -->
        <div class="card ai-org-card">
          <div class="ai-org-header">
            <div class="ai-org-title-wrap">
              <div class="ai-icon-chip">
                <Icon name="sparkles" :size="16" />
              </div>
              <div>
                <div class="ai-title-row">
                  <h4>AI-разбор центра</h4>
                  <span class="badge badge-purple">AI-анализ</span>
                </div>
                <p class="muted sub-text">Анализ позиционирования и программирования мероприятий</p>
              </div>
            </div>

            <button
              class="btn-refresh"
              :disabled="aiLoading"
              @click="loadAiOrg(true)"
              title="Обновить аналитический разбор"
            >
              <Icon name="refresh-cw" :size="13" :class="{ spinning: aiLoading }" />
              <span>{{ aiLoading ? 'Анализ...' : 'Обновить' }}</span>
            </button>
          </div>

          <div v-if="aiLoading && !aiResult" class="ai-org-loading">
            <div class="ai-pulse-bar" />
            <span class="muted">Формирование персонального аналитического разбора...</span>
          </div>

          <div v-else-if="aiError" class="ai-org-error">
            <Icon name="alert-triangle" :size="14" />
            <span>{{ aiError }}</span>
            <button class="btn-primary" style="font-size: 11px; padding: 2px 8px;" @click="loadAiOrg(true)">Повторить</button>
          </div>

          <div v-else-if="aiResult" class="ai-org-content">
            <div
              v-for="(sec, idx) in aiSections"
              :key="idx"
              class="ai-org-sec"
            >
              <div class="sec-mini-head">
                <span class="sec-dot" />
                <h5>{{ sec.title }}</h5>
              </div>

              <div v-if="sec.paragraphs.length" class="sec-mini-p">
                <p v-for="(p, pi) in sec.paragraphs" :key="pi" v-html="formatBold(p)" />
              </div>

              <ul v-if="sec.items.length" class="sec-mini-ul">
                <li v-for="(item, ii) in sec.items" :key="ii" v-html="formatBold(item)" />
              </ul>
            </div>

            <div class="ai-org-meta muted">
              <span>Сформировано: {{ aiResult.generated_at }}</span>
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

.ai-org-card {
  background: var(--surface);
  border: 1px solid rgba(139, 92, 246, 0.25);
  box-shadow: 0 4px 16px rgba(139, 92, 246, 0.05);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.ai-org-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 10px;
}
.ai-org-title-wrap { display: flex; gap: 10px; align-items: flex-start; }
.ai-icon-chip {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  background: var(--purple-wash);
  color: var(--purple);
  display: grid;
  place-items: center;
  flex-shrink: 0;
  margin-top: 1px;
}
.ai-title-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.ai-title-row h4 { font-size: 14px; font-weight: 700; margin: 0; }
.ai-org-loading {
  padding: 14px 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 12px;
}
.ai-pulse-bar {
  height: 2px;
  border-radius: 2px;
  background: linear-gradient(90deg, transparent, var(--purple), transparent);
  animation: pulseBar 1.5s infinite linear;
}
@keyframes pulseBar {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}
.ai-org-error {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--danger);
  background: var(--danger-wash);
  padding: 10px;
  border-radius: 6px;
}
.ai-org-content { display: flex; flex-direction: column; gap: 12px; }
.ai-org-sec {
  background: var(--raised);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.sec-mini-head { display: flex; align-items: center; gap: 6px; }
.sec-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--purple); }
.sec-mini-head h5 { font-size: 13px; font-weight: 700; margin: 0; }
.sec-mini-p p { font-size: 12px; line-height: 1.5; color: var(--text-primary); margin: 0; }
.sec-mini-p p + p { margin-top: 6px; }
.sec-mini-ul { margin: 2px 0 0 0; padding-left: 16px; display: flex; flex-direction: column; gap: 4px; }
.sec-mini-ul li { font-size: 12px; line-height: 1.45; color: var(--text-primary); }
.ai-org-meta {
  display: flex;
  gap: 8px;
  font-size: 11px;
  padding-top: 6px;
  border-top: 1px solid var(--border);
}
.btn-refresh { font-size: 11px; padding: 4px 8px; border-radius: 6px; gap: 4px; }
.spinning { animation: spin 1s linear infinite; }

@media (max-width: 680px) {
  .stats-grid {
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }
  .stat-card {
    padding: 10px;
  }
  .stat-card .value {
    font-size: 17px;
  }
  .two-cols {
    grid-template-columns: 1fr;
    gap: 12px;
  }
  .mini-card {
    padding: 12px;
  }
  .plan-card {
    padding: 12px;
  }
  .plan-meta {
    flex-direction: column;
    gap: 4px;
  }
  .ai-org-card {
    padding: 12px;
  }
}
</style>
