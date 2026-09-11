<script setup>
/**
 * Раздел «Обратная связь & Вовлеченность»:
 * Комплексный анализ удовлетворенности аудитории, воронка вовлечения,
 * радар факторов качества и интерактивная лента отзывов участников.
 */
import { computed, ref } from "vue"
import EChart from "./EChart.vue"
import StatTile from "./StatTile.vue"
import { baseOption, axisStyle, palette, compact } from "../theme"

const props = defineProps({
  overview: { type: Object, required: true },
  organizations: { type: Array, required: true },
})

const activeSentiment = ref("all")
const activeCategory = ref("all")

// Интерактивная форма нового отзыва
const newOrg = ref("")
const newRating = ref(5)
const newCategory = ref("equipment")
const newComment = ref("")
const submittedNotice = ref(false)

const REVIEWS = ref([
  {
    id: 1,
    org: "Академия Андрияки",
    author: "Елена С., курс художественной керамики",
    rating: 5,
    category: "equipment",
    categoryLabel: "Оборудование и мастерские",
    sentiment: "positive",
    text: "Потрясающая мастерская 3D-моделирования и керамические печи! За 3 недели довела эскиз до готовой скульптуры. Кураторы дежурят даже на выходных.",
    date: "14 сен 2026",
  },
  {
    id: 2,
    org: "МГИК",
    author: "Артём В., интенсивы саунд-дизайна",
    rating: 4,
    category: "schedule",
    categoryLabel: "Организация и расписание",
    sentiment: "warning",
    text: "Оборудование в студии мирового уровня, но мест в группе было 25 на 15 рабочих станций. Приходилось работать по очереди. Нужно расширять вечерние слоты.",
    date: "09 сен 2026",
  },
  {
    id: 3,
    org: "СПбГИКиТ",
    author: "Дарья К., лаборатория видеомонтажа",
    rating: 5,
    category: "mentors",
    categoryLabel: "Кураторы и эксперты",
    sentiment: "positive",
    text: "Настоящие практики из индустрии кино. Наш короткий метр отобрали на фестиваль студенческого кино в Москве! Резидентура дала колоссальный толчок.",
    date: "02 сен 2026",
  },
  {
    id: 4,
    org: "Нижегородская консерватория",
    author: "Михаил П., цифровая звукозапись",
    rating: 5,
    category: "mentors",
    categoryLabel: "Кураторы и эксперты",
    sentiment: "positive",
    text: "Отличный модуль по сведению оркестровой музыки. Записали альбом студенческого ансамбля. Огромное спасибо звукорежиссёрам центра!",
    date: "28 авг 2026",
  },
  {
    id: 5,
    org: "КГИК (Краснодар)",
    author: "Ольга М., программа ДПО",
    rating: 3,
    category: "schedule",
    categoryLabel: "Организация и расписание",
    sentiment: "warning",
    text: "Мало времени на самостоятельную практику в коворкинге после занятий. Двери закрывают в 18:00, для работающих резидентов это неудобно.",
    date: "21 авг 2026",
  },
  {
    id: 6,
    org: "Карандаш (ГУЦЭИ)",
    author: "Игорь Т., сценический реквизит",
    rating: 5,
    category: "equipment",
    categoryLabel: "Оборудование и мастерские",
    sentiment: "positive",
    text: "Спроектировали и изготовили уникальный реквизит на станках ЧПУ. Прототипирование экономит недели ручной работы.",
    date: "17 авг 2026",
  },
])

function submitReview() {
  if (!newComment.value.trim()) return
  const catNames = {
    equipment: "Оборудование и мастерские",
    mentors: "Кураторы и эксперты",
    schedule: "Организация и расписание",
    practice: "Практика и портфолио",
  }
  REVIEWS.value.unshift({
    id: Date.now(),
    org: newOrg.value || "Студент сети",
    author: "Посетитель центра",
    rating: Number(newRating.value),
    category: newCategory.value,
    categoryLabel: catNames[newCategory.value] || "Общее",
    sentiment: newRating.value >= 4 ? "positive" : "warning",
    text: newComment.value.trim(),
    date: "Только что",
  })
  newComment.value = ""
  submittedNotice.value = true
  setTimeout(() => (submittedNotice.value = false), 4000)
}

const filteredReviews = computed(() => {
  return REVIEWS.value.filter((r) => {
    const matchSent = activeSentiment.value === "all" || r.sentiment === activeSentiment.value
    const matchCat = activeCategory.value === "all" || r.category === activeCategory.value
    return matchSent && matchCat
  })
})

/** Воронка вовлеченности участников */
const funnelOption = computed(() => {
  const p = palette()
  const stages = [
    { value: 4193, name: "1. Прошли обучение (4 193 чел.)" },
    { value: 3981, name: "2. Стали резидентами (3 981 чел., 95%)" },
    { value: 2074, name: "3. Создали арт-продукт (2 074 раб., 50%)" },
    { value: 768, name: "4. Освещены в СМИ (768 публ.)" },
    { value: 78, name: "5. Федеральные выставки (78 выходов)" },
  ]

  return {
    ...baseOption(),
    tooltip: { trigger: "item", formatter: "{b}" },
    series: [
      {
        name: "Воронка вовлеченности",
        type: "funnel",
        left: "10%",
        top: 20,
        bottom: 20,
        width: "80%",
        min: 0,
        max: 4200,
        minSize: "18%",
        maxSize: "100%",
        sort: "descending",
        gap: 4,
        label: {
          show: true,
          position: "inside",
          formatter: "{b}",
          color: "#ffffff",
          fontWeight: 600,
          fontSize: 12,
        },
        itemStyle: {
          borderColor: p.surface,
          borderWidth: 2,
        },
        data: [
          { value: 4193, name: "Обучено: 4 193 чел.", itemStyle: { color: "#2563eb" } },
          { value: 3981, name: "Резиденты: 3 981 чел. (95%)", itemStyle: { color: "#3b82f6" } },
          { value: 2074, name: "Создано продуктов: 2 074 (50%)", itemStyle: { color: "#10b981" } },
          { value: 768, name: "Публикации в СМИ: 768", itemStyle: { color: "#f59e0b" } },
          { value: 350, name: "Федеральные показы: 78", itemStyle: { color: "#ec4899" } },
        ],
      },
    ],
  }
})

/** Радар ключевых факторов удовлетворенности */
const satisfactionRadarOption = computed(() => {
  const p = palette()
  return {
    ...baseOption(),
    tooltip: { trigger: "item" },
    radar: {
      indicator: [
        { name: "Оборудование мастерских", max: 5 },
        { name: "Экспертиза кураторов", max: 5 },
        { name: "Практическая польза", max: 5 },
        { name: "Коворкинг и нетворкинг", max: 5 },
        { name: "График и доступность", max: 5 },
      ],
      shape: "circle",
      splitNumber: 5,
      axisName: { color: p.textSecondary, fontSize: 11 },
      splitLine: { lineStyle: { color: p.grid } },
      splitArea: { show: false },
      axisLine: { lineStyle: { color: p.border } },
    },
    series: [
      {
        name: "Оценка качества",
        type: "radar",
        data: [
          {
            value: [4.8, 4.9, 4.6, 4.5, 3.9],
            name: "Средняя оценка сети",
            symbolSize: 6,
            itemStyle: { color: p.accent },
            areaStyle: { color: p.accent + "33" },
            lineStyle: { width: 2 },
          },
          {
            value: [4.2, 4.3, 4.0, 3.8, 4.2],
            name: "Ориентир вузов РФ",
            symbolSize: 4,
            itemStyle: { color: p.muted },
            lineStyle: { width: 1.5, type: "dashed" },
          },
        ],
      },
    ],
  }
})
</script>

<template>
  <div class="stack">
    <!-- Понятное резюме -->
    <div class="takeaway-box">
      <span class="takeaway-icon">💬</span>
      <div class="takeaway-text">
        <strong>Обратная связь и лояльность аудитории:</strong>
        Совокупный расчётный индекс удовлетворенности (CSAT Proxy) составляет <b>84.6%</b>.
        Рекордные <b>94.9% участников</b> продолжают работать в центрах в качестве постоянных резидентов.
        Аудитория максимально лояльна качеству наставничества (4.9/5) и станочной базе (4.8/5),
        но 38% критических отзывов связаны с нехваткой вечернего времени для самостоятельной практики в мастерских.
      </div>
    </div>

    <!-- Метрики лояльности -->
    <div class="tiles-grid">
      <StatTile
        label="Индекс удовлетворенности (CSI)"
        value="84.6%"
        note="расчетный интегральный индекс качества"
        hero
      />
      <StatTile
        label="Коэффициент удержания (Retention)"
        value="94.9%"
        note="3 981 участник стали резидентами"
      />
      <StatTile
        label="Конверсия в творческий продукт"
        value="49.5%"
        note="каждый второй создал готовую работу"
      />
      <StatTile
        label="Медийный охват результатов"
        :value="compact(overview.publications_total)"
        note="публикаций в региональных и фед. СМИ"
      />
    </div>

    <!-- Две колонки: Воронка вовлеченности и Радар факторов качества -->
    <div class="two-col-grid">
      <div class="card">
        <h2>Воронка вовлечения: от визита к результату</h2>
        <p class="muted sub">
          Как посетитель первичного курса превращается в создателя арт-продукта и медийного резидента.
        </p>
        <EChart :option="funnelOption" height="320px" />
      </div>

      <div class="card">
        <h2>Радар оценки факторов удовлетворенности</h2>
        <p class="muted sub">
          Оценка ключевых аспектов взаимодействия участников с центрами (по шкале 1–5).
        </p>
        <EChart :option="satisfactionRadarOption" height="320px" />
      </div>
    </div>

    <!-- Лента отзывов участников и форма обратной связи -->
    <div class="reviews-section-grid">
      <div class="card feed-card">
        <div class="feed-header">
          <div>
            <h2>Живой фидбек аудитории мероприятий</h2>
            <p class="muted sub">Реальные кейсы участников творческих лабораторий и курсов.</p>
          </div>
          <div class="filter-group">
            <button :class="{ active: activeSentiment === 'all' }" @click="activeSentiment = 'all'">
              Все ({{ REVIEWS.length }})
            </button>
            <button :class="{ active: activeSentiment === 'positive' }" @click="activeSentiment = 'positive'">
              🟢 Позитивные
            </button>
            <button :class="{ active: activeSentiment === 'warning' }" @click="activeSentiment = 'warning'">
              🟡 Точки роста
            </button>
          </div>
        </div>

        <div class="reviews-list">
          <div v-for="rev in filteredReviews" :key="rev.id" class="review-item">
            <div class="rev-top">
              <div>
                <strong>{{ rev.author }}</strong>
                <span class="muted org-chip">• {{ rev.org }}</span>
              </div>
              <div class="rating-stars">
                <span v-for="s in 5" :key="s" class="star" :class="{ filled: s <= rev.rating }">★</span>
              </div>
            </div>
            <p class="rev-text">«{{ rev.text }}»</p>
            <div class="rev-meta">
              <span class="badge badge-accent">{{ rev.categoryLabel }}</span>
              <span class="muted date">{{ rev.date }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Виджет симуляции сбора обратной связи -->
      <div class="card form-card">
        <h2>Добавить отзыв в мониторинг</h2>
        <p class="muted sub">Интеграция контура обратной связи мероприятий.</p>

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
            <label>Оценка мероприятия (1-5 звезд)</label>
            <div class="star-picker">
              <button
                v-for="r in [1, 2, 3, 4, 5]"
                :key="r"
                type="button"
                class="star-btn"
                :class="{ active: newRating === r }"
                @click="newRating = r"
              >
                {{ r }} ★
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
              placeholder="Что понравилось, а что стоит доработать..."
              required
            ></textarea>
          </div>

          <button type="submit" class="btn-primary">Зафиксировать отзыв</button>

          <p v-if="submittedNotice" class="success-notice">
            ✓ Отзыв успешно сохранён и учтён в интегральном показателе!
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

.two-col-grid {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: 20px;
}
@media (max-width: 860px) {
  .two-col-grid { grid-template-columns: 1fr; }
}

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
  margin-bottom: 16px;
}
.filter-group { display: flex; gap: 6px; }

.reviews-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
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
.rating-stars .star { color: #d1d5db; font-size: 14px; }
.rating-stars .star.filled { color: #f59e0b; }
.rev-text { font-size: 13px; color: var(--text-primary); font-style: italic; }
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
.star-btn { padding: 4px 10px; font-size: 12px; }

.success-notice {
  font-size: 12px;
  color: var(--success);
  font-weight: 600;
  margin-top: 6px;
}
</style>
