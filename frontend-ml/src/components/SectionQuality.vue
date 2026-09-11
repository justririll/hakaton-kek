<script setup>
/** Качество данных: аномалии отчётности и находки разбора исходных книг. */
import { computed, ref } from 'vue'
import { SEVERITY } from '../theme'

const props = defineProps({
  anomalies: { type: Array, required: true },
  quality: { type: Object, required: true },
})

const severity = ref('all')

const KINDS = {
  inconsistency: 'противоречие в отчёте',
  outlier: 'статистический выброс',
  multivariate: 'нетипичный профиль',
}

const filtered = computed(() =>
  props.anomalies.filter((a) => severity.value === 'all' || a.severity === severity.value),
)

const counts = computed(() => {
  const result = {}
  for (const a of props.anomalies) result[a.severity] = (result[a.severity] || 0) + 1
  return result
})

/** Находки разбора: только содержательные, без строк «пустая ячейка → 0». */
const parseIssues = computed(() =>
  (props.quality.issues || []).filter((i) => i.severity !== 'info'),
)

const imputed = computed(() =>
  (props.quality.issues || []).filter((i) => i.kind === 'imputed_zero').length,
)
</script>

<template>
  <div class="stack">
    <div class="card">
      <h2>Откуда берутся цифры</h2>
      <p class="muted sub">
        Двадцать центров присылают один и тот же бланк, но заполняют его по-разному:
        где-то рубли, где-то тысячи рублей, где-то строка просто пропущена. Прежде чем
        сравнивать центры, всё это нужно привести к общему виду — и честно показать,
        что именно пришлось поправить.
      </p>
      <div class="tiles">
        <div class="tile">
          <div class="tile-value">{{ quality.organizations }}</div>
          <div class="tile-label">отчётов прочитано без потерь</div>
        </div>
        <div class="tile">
          <div class="tile-value">{{ Math.round(quality.cell_coverage * 100) }} %</div>
          <div class="tile-label">показателей на месте после обработки</div>
        </div>
        <div class="tile">
          <div class="tile-value">{{ parseIssues.length }}</div>
          <div class="tile-label">расхождения пришлось разбирать вручную</div>
        </div>
        <div class="tile">
          <div class="tile-value">{{ imputed }}</div>
          <div class="tile-label">пустых строк прочитаны как «такого не было»</div>
        </div>
      </div>

      <table class="issues">
        <thead>
          <tr>
            <th>Организация</th>
            <th>Показатель</th>
            <th>Что сделано</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(issue, i) in parseIssues" :key="i">
            <td class="nowrap">{{ issue.org_id }}</td>
            <td class="nowrap muted">{{ issue.indicator || '—' }}</td>
            <td>{{ issue.message }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="card">
      <h2>Что выглядит подозрительно</h2>
      <p class="muted sub">
        Красным помечено то, где цифры внутри отчёта противоречат друг другу — такие
        случаи нужно перепроверить у центра. Серым — просто резкие отличия от остальных:
        это не ошибка, так выглядят и лидеры, и отстающие.
      </p>
      <div class="filters">
        <button :class="{ active: severity === 'all' }" @click="severity = 'all'">
          все · {{ anomalies.length }}
        </button>
        <button
          v-for="(value, key) in counts"
          :key="key"
          :class="{ active: severity === key }"
          @click="severity = key"
        >
          <span class="severity-dot" :style="{ backgroundColor: SEVERITY[key].color }" />
          <span>{{ SEVERITY[key].label }} · {{ value }}</span>
        </button>
      </div>
      <div class="scroll-x">
        <table>
          <thead>
            <tr>
              <th>Уровень</th>
              <th>Центр</th>
              <th>Тип</th>
              <th>Находка</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in filtered" :key="i">
              <td class="nowrap">
                <span class="badge" :style="{ borderColor: SEVERITY[row.severity].color, color: SEVERITY[row.severity].color }">
                  {{ SEVERITY[row.severity].label }}
                </span>
              </td>
              <td class="nowrap">{{ row.org_name }}</td>
              <td class="nowrap muted">{{ KINDS[row.kind] || row.kind }}</td>
              <td class="what">{{ row.message }}</td>
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
.severity-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-right: 6px; }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin: 18px 0; }
.tile-value { font-size: 22px; font-weight: 600; letter-spacing: -0.02em; }
.tile-label { font-size: 12px; color: var(--text-secondary); margin-top: 2px; }
.issues { margin-top: 8px; }
.filters { display: flex; flex-wrap: wrap; gap: 8px; margin: 16px 0; }
.nowrap { white-space: nowrap; }
.what { font-size: 12px; color: var(--text-secondary); max-width: 70ch; }
</style>
