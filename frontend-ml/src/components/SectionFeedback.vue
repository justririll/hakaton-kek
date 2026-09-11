<script setup>
/**
 * Раздел «Обратная связь и вовлечённость».
 *
 * Прямой обратной связи в ведомственной отчётности нет: ни оценок, ни отзывов,
 * ни NPS. Раздел построен на наблюдаемых заменителях, которые отвечают на тот
 * же управленческий вопрос «доволен ли участник и вернулся ли он»:
 *
 *   довёл ли участник работу до результата  → конверсия в арт-продукт;
 *   вернулся ли он                          → доля резидентов;
 *   заметен ли результат снаружи            → публикации и федеральные площадки.
 *
 * Ни одно число здесь не выдумано: всё приходит из API. Контур для настоящей
 * обратной связи предусмотрен ниже и прямо помечен как неподключённый.
 */
import { computed, ref } from "vue"
import EChart from "./EChart.vue"
import StatTile from "./StatTile.vue"
import { axisStyle, baseOption, compact, palette, percent } from "../theme"

const props = defineProps({
  overview: { type: Object, required: true },
  organizations: { type: Array, required: true },
})

// --- наблюдаемые заменители обратной связи --------------------------------------

/** Доля участников, доведших работу до готового арт-продукта. */
const productRate = computed(() => {
  const aud = props.overview?.audience_total || 0
  return aud ? (props.overview?.products_total || 0) / aud : 0
})

/** Доля аудитории, дошедшей до статуса резидента (строка 3 Формы 2). */
const residentRate = computed(() => {
  const aud = props.overview?.audience_total || 0
  return aud ? (props.overview?.residents_total || 0) / aud : 0
})

/** Центры с конверсией ниже сетевой медианы — куда смотреть в первую очередь. */
const belowMedian = computed(() => {
  const median = props.overview?.median_product_rate ?? 0
  return props.organizations.filter((o) => (o.product_rate ?? 0) < median).length
})

/**
 * Ступени вовлечённости. Единицы на ступенях разные (люди → люди → работы →
 * публикации → события), поэтому это не вложенная воронка, а сужение от
 * участия к внешнему признанию. Значение каждой ступени равно наблюдаемому
 * показателю — геометрия не «рисуется» отдельно от подписи.
 */
const funnelOption = computed(() => {
  const p = palette()
  const o = props.overview || {}
  const stages = [
    { value: o.audience_total || 0, name: `Обучено участников: ${compact(o.audience_total)} чел.`, color: "#2563eb" },
    { value: o.residents_total || 0, name: `Резиденты: ${compact(o.residents_total)} чел.`, color: "#3b82f6" },
    { value: o.products_total || 0, name: `Готовые арт-продукты: ${compact(o.products_total)} шт.`, color: "#10b981" },
    { value: o.publications_total || 0, name: `Публикации о результатах: ${compact(o.publications_total)} шт.`, color: "#f59e0b" },
    { value: o.federal_events_total || 0, name: `Федеральные площадки: ${compact(o.federal_events_total)} шт.`, color: "#8b5cf6" },
  ]

  return {
    ...baseOption(),
    tooltip: { trigger: "item", formatter: "{b}" },
    series: [
      {
        name: "Ступени вовлечённости",
        type: "funnel",
        left: "6%",
        top: 16,
        bottom: 16,
        width: "88%",
        min: 0,
        max: stages[0].value,
        minSize: "22%",
        maxSize: "100%",
        sort: "descending",
        gap: 4,
        label: { show: true, position: "inside", formatter: "{b}", color: "#ffffff", fontWeight: 600, fontSize: 12 },
        itemStyle: { borderColor: p.surface, borderWidth: 2, borderRadius: 4 },
        data: stages.map((s) => ({ value: s.value, name: s.name, itemStyle: { color: s.color } })),
      },
    ],
  }
})

/**
 * Конверсия участия в результат по центрам — то, что в этой отчётности ближе
 * всего к оценке удовлетворённости: участник, доведший работу до конца,
 * проголосовал за центр делом.
 */
const conversionOption = computed(() => {
  const p = palette()
  const rows = [...props.organizations]
    .filter((o) => (o.audience_total || 0) > 0)
    .sort((a, b) => (b.product_rate || 0) - (a.product_rate || 0))
  const median = props.overview?.median_product_rate ?? 0

  return {
    ...baseOption(),
    tooltip: {
      ...baseOption().tooltip,
      trigger: "item",
      formatter: (item) => {
        const org = rows[item.dataIndex]
        return `<b>${org.short_name}</b><br/>${item.value.toFixed(2)} работ на участника<br/>`
          + `${compact(org.products_total)} шт. на ${compact(org.audience_total)} чел.`
      },
    },
    grid: { left: 8, right: 24, top: 28, bottom: 8, containLabel: true },
    xAxis: { type: "value", ...axisStyle(), axisLabel: { color: p.muted, fontSize: 11 } },
    yAxis: {
      type: "category",
      inverse: true,
      data: rows.map((o) => o.short_name),
      ...axisStyle(),
      axisLabel: { color: p.textSecondary, fontSize: 11 },
    },
    series: [
      {
        type: "bar",
        data: rows.map((o) => ({
          value: Number((o.product_rate || 0).toFixed(3)),
          itemStyle: { color: (o.product_rate || 0) >= median ? "#10b981" : "#f59e0b", borderRadius: [0, 3, 3, 0] },
        })),
        barMaxWidth: 14,
        markLine: {
          silent: true,
          symbol: "none",
          // «end» у вертикальной линии ложится на подписи оси — уводим внутрь сверху.
          label: {
            formatter: `медиана ${median}`,
            color: p.muted,
            fontSize: 11,
            position: "insideEndTop",
          },
          lineStyle: { color: p.muted, width: 1, type: "dashed" },
          data: [{ xAxis: median }],
        },
      },
    ],
  }
})

// --- контур сбора настоящей обратной связи ---------------------------------------

// Источника отзывов нет, поэтому лента пуста. Всё, что появится здесь, —
// записи, введённые прямо в интерфейсе; они помечаются как демонстрационные и
// нигде не участвуют в расчётах.
const demoEntries = ref([])

const newOrg = ref("")
const newRating = ref(5)
const newCategory = ref("equipment")
const newComment = ref("")
const submittedNotice = ref(false)

const CATEGORY_LABELS = {
  equipment: "Оборудование и мастерские",
  mentors: "Кураторы и эксперты",
  schedule: "Организация и расписание",
  practice: "Практика и портфолио",
}

function submitReview() {
  if (!newComment.value.trim()) return
  demoEntries.value.unshift({
    id: Date.now(),
    org: newOrg.value || "центр не указан",
    rating: Number(newRating.value),
    categoryLabel: CATEGORY_LABELS[newCategory.value] || "Общее",
    text: newComment.value.trim(),
  })
  newComment.value = ""
  submittedNotice.value = true
}
</script>

<template>
  <div class="stack">
    <!-- Резюме -->
    <div class="takeaway-box">
      <div class="takeaway-text">
        <strong>Прямой обратной связи в отчётности нет.</strong>
        Формы 1 и 2 не содержат ни оценок, ни отзывов, ни NPS — и выдумывать их означало бы
        строить управленческие решения на несуществующих числах. Вместо этого раздел опирается на
        наблюдаемые заменители: участник, <b>доведший работу до результата</b>, и участник,
        <b>вернувшийся резидентом</b>, проголосовали за центр делом.
        По сети это {{ percent(productRate, 1) }} конверсии в готовый арт-продукт и
        {{ compact(overview.residents_total) }} резидентов;
        <b>{{ belowMedian }} из {{ overview.organizations }} центров</b> идут ниже сетевой медианы
        {{ overview.median_product_rate }} работы на участника — это и есть адресный список для работы.
      </div>
    </div>

    <!-- Наблюдаемые показатели вовлечённости -->
    <div class="tiles-grid">
      <StatTile
        label="Конверсия в арт-продукт"
        :value="percent(productRate, 1)"
        note="готовых работ на участника по сети"
        hero
      />
      <StatTile
        label="Медиана по центрам"
        :value="`${overview.median_product_rate}`"
        note="работы на участника у типичного центра"
      />
      <StatTile
        label="Резиденты"
        :value="compact(overview.residents_total)"
        note="строка 3 Формы 2 — вернувшиеся к работе"
      />
      <StatTile
        label="Внешнее признание"
        :value="compact(overview.publications_total)"
        :note="`публикаций и ${overview.federal_events_total} выходов на федеральные площадки`"
      />
    </div>

    <!-- Две колонки: ступени вовлечённости и конверсия по центрам -->
    <div class="two-col-grid">
      <div class="card">
        <h2>Ступени вовлечённости: от участия к признанию</h2>
        <p class="muted sub">
          Единицы на ступенях разные (люди → люди → работы → публикации → события), поэтому это не
          вложенная воронка: ступени показывают, насколько сужается путь от посещения к внешнему
          результату. Высота каждой ступени равна наблюдаемому значению показателя.
        </p>
        <EChart :option="funnelOption" height="320px" />
      </div>

      <div class="card">
        <h2>Конверсия участия в результат по центрам</h2>
        <p class="muted sub">
          Сколько готовых работ приходится на одного участника. Жёлтым — центры ниже сетевой медианы:
          аудитория до них дошла, но результата не получила.
        </p>
        <EChart :option="conversionOption" height="480px" />
      </div>
    </div>

    <!-- Контур сбора настоящей обратной связи -->
    <div class="reviews-section-grid">
      <div class="card feed-card">
        <div class="feed-header">
          <div>
            <h2>Лента обратной связи</h2>
            <p class="muted sub">
              Источник не подключён: полей отзывов в Формах 1 и 2 не существует.
            </p>
          </div>
        </div>

        <div v-if="demoEntries.length" class="reviews-list">
          <div v-for="entry in demoEntries" :key="entry.id" class="review-item">
            <div class="rev-top">
              <div>
                <strong>{{ entry.org }}</strong>
                <span class="muted org-chip">• демонстрационная запись</span>
              </div>
              <div class="rating-badge mono-nums">{{ entry.rating }}.0 / 5.0</div>
            </div>
            <p class="rev-text">«{{ entry.text }}»</p>
            <div class="rev-meta">
              <span class="badge badge-neutral">{{ entry.categoryLabel }}</span>
              <span class="muted date">введено в интерфейсе, в расчётах не участвует</span>
            </div>
          </div>
        </div>

        <div v-else class="empty-feed">
          <p>
            Здесь будут отзывы, когда появится источник. Пока лента пуста — и это честное состояние
            данных, а не ошибка загрузки.
          </p>
          <p class="muted">
            Чтобы контур заработал, нужны две вещи: запись показателя в
            <code>app/ingest/schema.py</code> и вызов <code>POST /api/reload</code> — после этого
            оценки пойдут в те же модели, что и остальные показатели, а раздел заполнится сам.
          </p>
        </div>
      </div>

      <!-- Форма сбора фидбека -->
      <div class="card form-card">
        <h2>Проверить контур</h2>
        <p class="muted sub">
          Форма показывает, как выглядит приём оценки. Запись остаётся в браузере и ни на что не влияет.
        </p>

        <form @submit.prevent="submitReview" class="review-form">
          <div class="field">
            <label>Учреждение культуры</label>
            <select v-model="newOrg">
              <option value="">Выберите центр...</option>
              <option v-for="o in organizations" :key="o.org_id" :value="o.short_name">
                {{ o.short_name }}
              </option>
            </select>
          </div>

          <div class="field">
            <label>Оценка мероприятия (баллы 1–5)</label>
            <div class="star-picker">
              <button
                v-for="r in [1, 2, 3, 4, 5]"
                :key="r"
                type="button"
                class="star-btn"
                :class="{ active: newRating === r }"
                @click="newRating = r"
              >
                {{ r }}.0
              </button>
            </div>
          </div>

          <div class="field">
            <label>Направление отзыва</label>
            <select v-model="newCategory">
              <option value="equipment">Оборудование и мастерские</option>
              <option value="mentors">Кураторы и эксперты</option>
              <option value="schedule">Организация и расписание</option>
              <option value="practice">Практика и портфолио</option>
            </select>
          </div>

          <div class="field">
            <label>Текст отзыва / предложения</label>
            <textarea
              v-model="newComment"
              rows="3"
              placeholder="Что понравилось, а что требует доработки..."
              required
            ></textarea>
          </div>

          <button type="submit" class="btn-primary">Зафиксировать отзыв</button>

          <p v-if="submittedNotice" class="success-notice">
            Запись добавлена в ленту как демонстрационная — в показатели она не попадает.
          </p>
        </form>
      </div>
    </div>
  </div>
</template>


<style scoped>
.stack { display: flex; flex-direction: column; gap: 24px; }
.sub { font-size: 13px; margin-top: 2px; }

.tiles-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 14px;
}

.two-col-grid > * { min-width: 0; }
.two-col-grid {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: 20px;
}
@media (max-width: 860px) {
  .two-col-grid { grid-template-columns: 1fr; }
}

.reviews-section-grid > * { min-width: 0; }
.reviews-section-grid {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 20px;
}
@media (max-width: 960px) {
  .reviews-section-grid { grid-template-columns: 1fr; }
}

.feed-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 14px;
}
.filter-group { display: flex; gap: 4px; }

.reviews-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 480px;
  overflow-y: auto;
}
.review-item {
  background: var(--raised);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.rev-top { display: flex; justify-content: space-between; align-items: center; }
.org-chip { font-size: 12px; }
.rating-badge {
  font-size: 11px;
  font-weight: 700;
  background: var(--surface);
  border: 1px solid var(--border);
  padding: 2px 6px;
  border-radius: 6px;
  color: var(--accent);
}
.rev-text { font-size: 13px; color: var(--text-primary); font-style: italic; line-height: 1.5; }
.rev-meta { display: flex; justify-content: space-between; align-items: center; font-size: 11px; margin-top: 4px; }

.review-form { display: flex; flex-direction: column; gap: 14px; margin-top: 14px; }
.field { display: flex; flex-direction: column; gap: 5px; }
.field label { font-size: 12px; font-weight: 600; color: var(--text-secondary); }
.field textarea {
  font: inherit;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 8px 12px;
  color: var(--text-primary);
  outline: none;
  resize: vertical;
}
.field textarea:focus { border-color: var(--accent); }
.star-picker { display: flex; gap: 6px; }
.star-btn { padding: 5px 12px; font-size: 12px; font-weight: 600; }

.success-notice {
  font-size: 12px;
  color: var(--success);
  font-weight: 600;
  margin-top: 4px;
}
.empty-feed {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 18px 16px;
  margin-top: 14px;
  border: 1px dashed var(--border);
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.55;
}
.empty-feed code {
  font-size: 12px;
  padding: 1px 5px;
  border-radius: 4px;
  background: var(--surface-2, rgba(127, 127, 127, 0.14));
}
</style>
