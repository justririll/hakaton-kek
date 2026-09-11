<script setup>
/** Рекомендации по программированию: фильтры, оценка эффекта, обоснование. */
import { computed, ref } from 'vue'
import EChart from './EChart.vue'
import { axisStyle, baseOption, compact, money, palette } from '../theme'

const props = defineProps({
  recommendations: { type: Array, required: true },
  types: { type: Object, required: true },
  summary: { type: Object, required: true },
})

const activeType = ref('all')
const minPriority = ref(0)

const filtered = computed(() =>
  props.recommendations
    .filter((r) => activeType.value === 'all' || r.rec_type === activeType.value)
    .filter((r) => r.priority >= minPriority.value)
    .sort((a, b) => b.priority - a.priority),
)

const typeOptions = computed(() => {
  const counts = {}
  for (const r of props.recommendations) counts[r.rec_type] = (counts[r.rec_type] || 0) + 1
  return Object.entries(counts).sort((a, b) => b[1] - a[1])
})

function impact(row) {
  if (row.impact_metric === 'revenue') return `+${money(row.impact_value)}`
  return `+${compact(row.impact_value)} ${row.impact_unit}`
}

/** Топ резервов: одна серия, значения подписаны у конца столбика. */
const topOption = computed(() => {
  const p = palette()
  const rows = filtered.value.slice(0, 12).reverse()
  return {
    ...baseOption(),
    grid: { left: 8, right: 56, top: 12, bottom: 8, containLabel: true },
    tooltip: {
      ...baseOption().tooltip,
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (items) => {
        const row = rows[items[0].dataIndex]
        return `<b>${row.org_name}</b><br/>${row.title}<br/>эффект: ${impact(row)}`
      },
    },
    xAxis: { type: 'value', ...axisStyle(), max: 100 },
    yAxis: {
      type: 'category',
      data: rows.map((r) => `${r.org_name} · ${r.title}`),
      ...axisStyle(),
      splitLine: { show: false },
      axisLabel: { color: p.muted, fontSize: 11, width: 260, overflow: 'truncate' },
    },
    series: [
      {
        name: 'Приоритет',
        type: 'bar',
        barMaxWidth: 16,
        itemStyle: { color: p.accent, borderRadius: [0, 4, 4, 0] },
        label: {
          show: true,
          position: 'right',
          color: p.textSecondary,
          fontSize: 11,
          formatter: (item) => impact(rows[item.dataIndex]),
        },
        data: rows.map((r) => r.priority),
      },
    ],
  }
})
</script>

<template>
  <div class="stack">
    <div class="card">
      <h2>Где лежит управленческий резерв</h2>
      <p class="muted sub">
        Каждая рекомендация получена сравнением центра с его кластером — организациями с
        похожей аудиторной моделью, исключая сам центр. Разрыв с эталоном группы означает
        резерв, который уже закрыт кем-то в сопоставимых условиях. Приоритет — место резерва
        в очереди по сети: 90 означает верхние 10 %.
      </p>
      <div class="totals">
        <div v-for="(value, metric) in summary.impact" :key="metric" class="total">
          <div class="total-value">
            {{ metric === 'revenue' ? money(value.total) : `${compact(value.total)} ${value.unit}` }}
          </div>
          <div class="total-label">
            {{
              {
                participants: 'участников',
                products: 'творческих продуктов',
                revenue: 'объёма услуг',
                publications: 'публикаций',
                formats: 'мероприятий к плану',
              }[metric] || metric
            }}
            <span class="muted">· {{ value.count }} рекомендаций</span>
          </div>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="filters">
        <button :class="{ active: activeType === 'all' }" @click="activeType = 'all'">
          все · {{ recommendations.length }}
        </button>
        <button
          v-for="[type, count] in typeOptions"
          :key="type"
          :class="{ active: activeType === type }"
          @click="activeType = type"
        >
          {{ types[type] || type }} · {{ count }}
        </button>
        <label class="slider">
          приоритет от {{ minPriority }}
          <input v-model.number="minPriority" type="range" min="0" max="100" step="5" />
        </label>
      </div>
      <EChart :option="topOption" height="380px" />
    </div>

    <div class="card">
      <h2>Список рекомендаций</h2>
      <p class="muted sub">
        Таблица — полный эквивалент графика: значение каждого резерва читается здесь без
        наведения.
      </p>
      <div class="scroll-x">
        <table>
          <thead>
            <tr>
              <th class="num">Приоритет</th>
              <th>Центр</th>
              <th>Рекомендация</th>
              <th class="num">Эффект</th>
              <th class="num">Доверие</th>
              <th>Обоснование и действие</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in filtered" :key="i">
              <td class="num strong">{{ row.priority }}</td>
              <td class="nowrap">{{ row.org_name }}</td>
              <td>
                {{ row.title }}
                <div class="muted tag">{{ types[row.rec_type] || row.rec_type }}</div>
              </td>
              <td class="num nowrap strong">{{ impact(row) }}</td>
              <td class="num">{{ row.confidence }}</td>
              <td class="why">
                {{ row.rationale }}
                <div class="action">→ {{ row.action }}</div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.stack { display: flex; flex-direction: column; gap: 20px; }
.sub { font-size: 13px; margin-top: 6px; max-width: 82ch; }
.totals { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-top: 18px; }
.total-value { font-size: 22px; font-weight: 600; letter-spacing: -0.02em; }
.total-label { font-size: 12px; color: var(--text-secondary); margin-top: 2px; }
.filters { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 16px; }
.slider { font-size: 12px; color: var(--muted); display: inline-flex; gap: 8px; align-items: center; margin-left: auto; }
.slider input { accent-color: var(--accent); }
.nowrap { white-space: nowrap; }
.strong { font-weight: 600; }
.tag { font-size: 11px; margin-top: 2px; }
.why { max-width: 52ch; font-size: 12px; color: var(--text-secondary); }
.action { margin-top: 6px; color: var(--text-primary); }
</style>
