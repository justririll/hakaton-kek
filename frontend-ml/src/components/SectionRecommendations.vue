<script setup>
/**
 * Что делать: карточки рекомендаций вместо плотной таблицы.
 *
 * Каждая карточка отвечает на три вопроса подряд — что не так, что сделать,
 * сколько это даст, — и показывает числа, на которых вывод построен. Термины
 * и служебные поля спрятаны в раскрывающийся блок.
 */
import { computed, ref } from 'vue'
import Disclosure from './Disclosure.vue'
import { count, money } from '../theme'

const props = defineProps({
  recommendations: { type: Array, required: true },
  summary: { type: Object, required: true },
})

// Человеческие названия вместо машинных типов правил.
const KIND = {
  fix_format: { label: 'Мало людей на мероприятиях', icon: '◔' },
  expand_format: { label: 'Формат работает — стоит расширить', icon: '↗' },
  launch_format: { label: 'Не хватает формата', icon: '+' },
  raise_conversion: { label: 'Приходят, но не доводят до результата', icon: '◑' },
  monetize: { label: 'Услуги можно продавать', icon: '₽' },
  amplify_visibility: { label: 'О работе мало кто знает', icon: '◌' },
  plan_risk: { label: 'План года под угрозой', icon: '!' },
}

const IMPACT_WORD = {
  participants: 'участников',
  products: 'готовых работ',
  revenue: 'объёма услуг',
  publications: 'публикаций',
  formats: 'мероприятий к плану',
}

const activeKind = ref('all')
const onlyImportant = ref(false)

/** Важность словами: число 0–100 руководителю ничего не говорит. */
function weight(priority) {
  if (priority >= 80) return { label: 'Высокая', level: 'high' }
  if (priority >= 50) return { label: 'Средняя', level: 'mid' }
  return { label: 'Обычная', level: 'low' }
}

function impactText(row) {
  const value = row.impact_metric === 'revenue' ? money(row.impact_value) : count(row.impact_value)
  return `+${value} ${row.impact_metric === 'revenue' ? '' : IMPACT_WORD[row.impact_metric] || row.impact_unit}`.trim()
}

/** Надёжность вывода словами: доля — это про размер и однородность группы. */
function reliability(confidence) {
  if (confidence >= 0.6) return 'высокая'
  if (confidence >= 0.35) return 'средняя'
  return 'предварительная'
}

const kinds = computed(() => {
  const counts = {}
  for (const r of props.recommendations) counts[r.rec_type] = (counts[r.rec_type] || 0) + 1
  return Object.entries(counts).sort((a, b) => b[1] - a[1])
})

const filtered = computed(() =>
  props.recommendations
    .filter((r) => activeKind.value === 'all' || r.rec_type === activeKind.value)
    .filter((r) => !onlyImportant.value || r.priority >= 80)
    .sort((a, b) => b.priority - a.priority),
)
</script>

<template>
  <div class="stack">
    <section class="card intro">
      <h2>Что делать</h2>
      <p class="lede">
        Каждое предложение получено сравнением центра с похожими на него — и только
        с ними. Если соседи по типу уже добиваются большего в тех же условиях,
        разрыв между ними и центром и есть резерв.
      </p>
      <div class="totals">
        <div v-for="(value, metric) in summary.impact" :key="metric" class="total">
          <div class="total-value">
            {{ metric === 'revenue' ? money(value.total) : count(value.total) }}
          </div>
          <div class="total-label">{{ IMPACT_WORD[metric] || metric }}</div>
        </div>
      </div>
    </section>

    <div class="filters">
      <button :class="{ active: activeKind === 'all' }" @click="activeKind = 'all'">
        Все · {{ recommendations.length }}
      </button>
      <button
        v-for="[kind, kindCount] in kinds"
        :key="kind"
        :class="{ active: activeKind === kind }"
        @click="activeKind = kind"
      >
        {{ KIND[kind]?.label || kind }} · {{ kindCount }}
      </button>
      <label class="switch">
        <input v-model="onlyImportant" type="checkbox" />
        только самое важное
      </label>
    </div>

    <div class="cards">
      <article v-for="(row, i) in filtered" :key="i" class="card rec">
        <header>
          <div class="who">
            <span class="icon">{{ KIND[row.rec_type]?.icon || '•' }}</span>
            <div>
              <div class="org">{{ row.org_name }}</div>
              <div class="kind">{{ KIND[row.rec_type]?.label || row.rec_type }}</div>
            </div>
          </div>
          <div class="weight" :class="weight(row.priority).level">
            <span class="dot" />
            {{ weight(row.priority).label }}
          </div>
        </header>

        <p class="problem">{{ row.rationale }}</p>

        <div class="action">
          <div class="action-label">Что сделать</div>
          <p>{{ row.action }}</p>
        </div>

        <footer>
          <div class="gain">
            <div class="gain-value">{{ impactText(row) }}</div>
            <div class="gain-note">ожидаемый эффект</div>
          </div>
          <div class="conf">
            надёжность вывода <b>{{ reliability(row.confidence) }}</b>
          </div>
        </footer>

        <Disclosure label="Числа, на которых построен вывод">
          <p v-if="row.evidence.peers">
            Сравнение шло по
            <b>{{ row.evidence.peers }}</b>
            центрам
            {{ row.evidence.scope === 'cluster' ? 'того же типа' : 'всей сети' }}<span
              v-if="row.evidence.best_peer"
              >, лучший результат у центра <b>{{ row.evidence.best_peer }}</b></span
            >.
          </p>
          <p>
            <span v-for="(value, key) in row.evidence" :key="key" class="kv">
              <span class="k">{{ key }}</span>
              <span class="v">{{ value }}</span>
            </span>
          </p>
          <p class="muted">
            Приоритет {{ row.priority }} из 100 — место этого резерва в общей очереди
            по сети. Доверие {{ row.confidence }} учитывает размер группы сравнения и
            разброс внутри неё.
          </p>
        </Disclosure>
      </article>
    </div>
  </div>
</template>

<style scoped>
.stack { display: flex; flex-direction: column; gap: 20px; }
.intro .lede { font-size: 14px; line-height: 1.6; color: var(--text-secondary); max-width: 70ch; margin-top: 8px; }
.totals { display: flex; flex-wrap: wrap; gap: 36px; margin-top: 22px; padding-top: 20px; border-top: 1px solid var(--border); }
.total-value { font-size: 24px; font-weight: 650; letter-spacing: -0.02em; }
.total-label { font-size: 12px; color: var(--text-secondary); margin-top: 2px; }

.filters { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.switch { display: inline-flex; gap: 7px; align-items: center; font-size: 12px; color: var(--muted); margin-left: auto; cursor: pointer; }
.switch input { accent-color: var(--accent); }

.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 16px; }
.rec { display: flex; flex-direction: column; }
.rec header { display: flex; justify-content: space-between; gap: 14px; align-items: flex-start; }
.who { display: flex; gap: 12px; align-items: center; }
.icon {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: var(--accent-wash);
  color: var(--accent);
  display: grid;
  place-items: center;
  font-size: 16px;
  flex: 0 0 auto;
}
.org { font-weight: 600; font-size: 14px; }
.kind { font-size: 12px; color: var(--muted); margin-top: 1px; }

.weight { display: inline-flex; align-items: center; gap: 6px; font-size: 11px; color: var(--text-secondary); white-space: nowrap; }
.dot { width: 7px; height: 7px; border-radius: 50%; background: var(--muted); }
.weight.high .dot { background: #d03b3b; }
.weight.mid .dot { background: #fab219; }

.problem { font-size: 13px; line-height: 1.6; color: var(--text-secondary); margin-top: 16px; flex: 1; }

.action { margin-top: 16px; padding: 12px 14px; border-left: 2px solid var(--accent); background: var(--accent-wash); border-radius: 0 8px 8px 0; }
.action-label { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: var(--accent); margin-bottom: 5px; }
.action p { font-size: 13px; line-height: 1.55; }

.rec footer { display: flex; justify-content: space-between; align-items: flex-end; gap: 14px; margin-top: 18px; padding-top: 16px; border-top: 1px solid var(--border); }
.gain-value { font-size: 20px; font-weight: 650; letter-spacing: -0.02em; }
.gain-note { font-size: 11px; color: var(--muted); margin-top: 1px; }
.conf { font-size: 11px; color: var(--muted); text-align: right; }
.conf b { color: var(--text-secondary); font-weight: 600; }

.kv { display: inline-flex; gap: 5px; margin: 0 10px 6px 0; font-size: 11px; }
.kv .k { color: var(--muted); }
.kv .v { font-variant-numeric: tabular-nums; }
</style>
