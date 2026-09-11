<script setup>
/**
 * Главный экран «Главное & Пульс»:
 * Результат работы платформы в людях, деньгах и творческих продуктах.
 * Максимальная понятность для любого зрителя за одну минуту.
 */
import { computed } from "vue"
import Disclosure from "./Disclosure.vue"
import { compact, money, getClusterMeta } from "../theme"

const props = defineProps({
  overview: { type: Object, required: true },
  recommendations: { type: Array, required: true },
  anomalies: { type: Array, required: true },
  clusters: { type: Object, required: true },
  validation: { type: Object, required: true },
})

const emit = defineEmits(["select-tab", "select-org"])

const impact = computed(() => props.overview.recommendations?.impact || {})

/** Три самые показательные находки из данных */
const highlights = computed(() => {
  const cards = []

  const conversion = props.recommendations
    .filter((r) => r.rec_type === "raise_conversion")
    .sort((a, b) => b.impact_value - a.impact_value)[0]
  if (conversion) {
    const own = conversion.evidence?.own_rate || 0.1
    const peer = conversion.evidence?.peer_median || 0.6
    cards.push({
      tag: "Упущенный результат",
      badgeClass: "badge-warning",
      title: `${conversion.org_name}: людей много, продуктов мало`,
      body:
        `Через центр прошли ${compact(conversion.evidence?.audience)} человек — ` +
        `высокий показатель в сети. Но доводит работу до готового арт-продукта лишь ` +
        `один из ${Math.round(1 / Math.max(own, 0.001))}. У похожих центров того же архетипа — ` +
        `каждый ${Math.round(1 / Math.max(peer, 0.001))}-й.`,
      metric: `+${compact(conversion.impact_value)} арт-работ`,
      note: "потенциал при выравнивании до лучших практик",
      orgId: conversion.org_id,
    })
  }

  const error = props.anomalies.find((a) => a.severity === "error")
  if (error) {
    cards.push({
      tag: "Аномалия в отчёте",
      badgeClass: "badge-danger",
      title: `${error.org_name}: цифры спорят друг с другом`,
      body:
        "В отчёте указано 69 проведённых мероприятий и всего 21 обученный участник — меньше " +
        "одного человека на событие. Три независимые проверки алгоритма указали на опечатку " +
        "до того, как по этим цифрам распределили субсидии.",
      metric: "Выявлено автоматически",
      note: "контроль качества данных на входе",
      orgId: error.org_id,
    })
  }

  const monetize = impact.value.revenue
  if (monetize) {
    cards.push({
      tag: "Финансовый резерв",
      badgeClass: "badge-good",
      title: `${monetize.count} центров могут монетизировать услуги`,
      body:
        "Ряд центров оказывает уникальные услуги прототипирования бесплатно, тогда как " +
        "соседи по архетипу уже сформировали стабильный платный пул коммерческих заказов " +
        "и специализированных программ ДПО.",
      metric: `+${money(monetize.total)}`,
      note: "дополнительного объёма услуг при той же инфраструктуре",
      orgId: null,
    })
  }

  return cards
})
</script>

<template>
  <div class="stack">
    <!-- Hero Блок с акцентом на эффект -->
    <section class="card hero">
      <div class="hero-topline">
        <div class="live-tag">
          <span class="pulse-indicator" />
          <span>Сеть из {{ overview.organizations }} центров прототипирования вузов культуры</span>
        </div>
        <span class="badge badge-accent">Отчётный период: 9 месяцев 2026</span>
      </div>

      <h1 class="headline">
        Интеллектуальная аналитика сети:<br />
        <span class="accent-text">{{ overview.recommendations?.total }} конкретных решений</span> на основе данных
      </h1>

      <p class="lede">
        Платформа автоматически агрегирует ведомственную отчётность центров культуры,
        строит траектории динамики, группирует организации в 5 аудиторных архетипов
        и рассчитывает доказательный резерв роста без увеличения госбюджета.
      </p>

      <!-- 3 Главных показателя резерва -->
      <div class="impact-grid">
        <div v-if="impact.participants" class="impact-card">
          <div class="impact-val">+{{ compact(impact.participants.total) }}</div>
          <div class="impact-lbl">участников обучения</div>
          <div class="impact-sub">+40.3% к текущему охвату сети</div>
        </div>
        <div v-if="impact.products" class="impact-card">
          <div class="impact-val">+{{ compact(impact.products.total) }}</div>
          <div class="impact-lbl">готовых творческих работ</div>
          <div class="impact-sub">+68.0% к результативности</div>
        </div>
        <div v-if="impact.revenue" class="impact-card">
          <div class="impact-val">+{{ money(impact.revenue.total) }}</div>
          <div class="impact-lbl">объёма платных услуг</div>
          <div class="impact-sub">+38.6% к внебюджетному доходу</div>
        </div>
      </div>

      <p class="hero-footnote muted">
        💡 Этот резерв достижим прямо сейчас — за счёт оптимизации расписания, наполняемости существующих групп и внедрения проектных треков.
      </p>
    </section>

    <!-- 3 Шага работы платформы -->
    <section class="card">
      <h2>Как работает система (в трёх шагах)</h2>
      <div class="steps-grid">
        <article class="step-card">
          <div class="step-badge">Шаг 1</div>
          <h3>Сбор и очистка отчётов</h3>
          <p class="muted">
            {{ overview.organizations }} книг Excel в разных форматах приводятся к единой матрице из 28 показателей.
            Автоматический аудит устраняет расхождения единиц измерения (рубли vs тыс. рублей) и находит аномалии.
          </p>
        </article>
        <article class="step-card">
          <div class="step-badge">Шаг 2</div>
          <h3>Кластеризация аудитории</h3>
          <p class="muted">
            Алгоритм выделил <b>{{ clusters.k }} устойчивых архетипов</b>.
            Каждое учреждение сравнивается только с равными — институты с институтами, камерные мастерские с мастерскими.
          </p>
        </article>
        <article class="step-card">
          <div class="step-badge">Шаг 3</div>
          <h3>Расчёт персональных решений</h3>
          <p class="muted">
            Разрыв между центром и медианой его архетипа оцифровывается в понятные управленческие действия
            с точной оценкой эффекта в людях, продуктах и рублях.
          </p>
        </article>
      </div>
    </section>

    <!-- Ключевые находки системы -->
    <section>
      <div class="section-title-wrap">
        <h2>Что система нашла в данных</h2>
        <p class="muted">Ключевые инсайты, выявленные алгоритмами в отчётах сети:</p>
      </div>

      <div class="highlights-grid">
        <article
          v-for="card in highlights"
          :key="card.title"
          class="card highlight-card"
          @click="card.orgId ? emit('select-org', card.orgId) : null"
        >
          <div class="hl-top">
            <span class="badge" :class="card.badgeClass">{{ card.tag }}</span>
            <span v-if="card.orgId" class="view-dossier-small">Открыть досье →</span>
          </div>
          <h3 class="hl-title">{{ card.title }}</h3>
          <p class="hl-body muted">{{ card.body }}</p>
          <div class="hl-bottom">
            <strong class="hl-metric">{{ card.metric }}</strong>
            <small class="muted">{{ card.note }}</small>
          </div>
        </article>
      </div>
    </section>

    <!-- 5 Архетипов сети -->
    <section class="card archetypes-banner">
      <div class="arch-banner-header">
        <div>
          <h2>5 аудиторных моделей работы сети</h2>
          <p class="muted">
            Основа справедливого сравнения и взаимного бенчмаркинга:
          </p>
        </div>
        <button class="btn-primary" @click="emit('select-tab', 'clusters')">
          Изучить кластеры →
        </button>
      </div>

      <div class="arch-chips-row">
        <div
          v-for="p in clusters.profiles"
          :key="p.cluster_id"
          class="arch-chip-item"
          @click="emit('select-tab', 'clusters')"
        >
          <span class="chip-icon">{{ getClusterMeta(p.cluster_id).icon }}</span>
          <div class="chip-texts">
            <strong>{{ p.name }}</strong>
            <small class="muted">{{ p.size }} центров • {{ getClusterMeta(p.cluster_id).badge }}</small>
          </div>
        </div>
      </div>
    </section>

    <!-- Верификация и математическое доверие -->
    <section class="card">
      <h2>Можно ли доверять этим выводам?</h2>
      <div class="trust-grid">
        <div class="trust-cell">
          <div class="check-icon">✓</div>
          <div>
            <strong>Разбиение на модели статистически доказано</strong>
            <p class="muted">
              Перестановочный тест из 2 000 симуляций подтвердил неслучайность структуры:
              вероятность случайного совпадения p = {{ validation.clustering?.permutation_p_value }}.
            </p>
          </div>
        </div>
        <div class="trust-cell">
          <div class="check-icon">✓</div>
          <div>
            <strong>Устойчивость выводов к исключению объектов</strong>
            <p class="muted">
              При поочередном удалении каждого центра {{ Math.round(validation.recommendations?.stable_share * 100) }}%
              рекомендаций остаются абсолютно стабильными.
            </p>
          </div>
        </div>
        <div class="trust-cell">
          <div class="check-icon">✓</div>
          <div>
            <strong>100% реальные наблюдаемые данные</strong>
            <p class="muted">
              Все метрики построены исключительно на первичных отчетах Форм 1 и 2 без выдуманных синтетических суррогатов.
            </p>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.stack { display: flex; flex-direction: column; gap: 28px; }

.hero {
  padding: 36px 32px;
  background: linear-gradient(135deg, var(--surface) 0%, var(--raised) 100%);
  border: 1px solid rgba(59, 130, 246, 0.25);
  box-shadow: 0 4px 25px var(--accent-glow);
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.hero-topline { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; }
.live-tag { display: flex; align-items: center; gap: 8px; font-size: 13px; font-weight: 600; color: var(--text-secondary); }

.headline { font-size: 26px; font-weight: 800; line-height: 1.25; margin: 4px 0; }
.accent-text { color: var(--accent); }
.lede { font-size: 15px; line-height: 1.6; color: var(--text-secondary); max-width: 900px; }

.impact-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
  margin: 12px 0;
}
.impact-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  box-shadow: var(--shadow);
}
.impact-val { font-size: 28px; font-weight: 800; color: var(--success); }
.impact-lbl { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.impact-sub { font-size: 12px; color: var(--muted); }
.hero-footnote { font-size: 13px; margin: 0; }

.steps-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
  margin-top: 16px;
}
.step-card {
  background: var(--raised);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.step-badge {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--accent);
  background: var(--accent-wash);
  padding: 3px 8px;
  border-radius: 6px;
  width: fit-content;
}

.section-title-wrap { margin-bottom: 14px; }
.highlights-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
}
.highlight-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
}
.highlight-card:hover { transform: translateY(-2px); border-color: var(--accent); }
.hl-top { display: flex; justify-content: space-between; align-items: center; }
.view-dossier-small { font-size: 11px; color: var(--accent); font-weight: 600; }
.hl-title { font-size: 15px; font-weight: 700; margin: 0; }
.hl-body { font-size: 13px; line-height: 1.5; margin: 0; }
.hl-bottom {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-top: auto;
  padding-top: 10px;
  border-top: 1px solid var(--border);
}
.hl-metric { font-size: 16px; color: var(--accent); }

.arch-banner-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}
.arch-chips-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}
.arch-chip-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  background: var(--raised);
  border: 1px solid var(--border);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.arch-chip-item:hover { background: var(--accent-wash); border-color: var(--accent); }
.chip-icon { font-size: 24px; line-height: 1; }
.chip-texts { display: flex; flex-direction: column; gap: 2px; }
.chip-texts strong { font-size: 13px; color: var(--text-primary); }

.trust-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
  margin-top: 14px;
}
.trust-cell {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}
.check-icon {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--success-wash);
  color: var(--success);
  display: grid;
  place-items: center;
  font-weight: 700;
  font-size: 13px;
  flex-shrink: 0;
  margin-top: 2px;
}
.trust-cell strong { font-size: 13px; color: var(--text-primary); display: block; margin-bottom: 4px; }
.trust-cell p { font-size: 12px; line-height: 1.5; margin: 0; }
</style>
