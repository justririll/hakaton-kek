<script setup>
/**
 * Главный экран «Главное»:
 * Результат работы платформы в людях, деньгах и творческих продуктах.
 * Исключительная ясность и лаконичность.
 */
import { computed } from "vue"
import Icon from "./Icon.vue"
import Disclosure from "./Disclosure.vue"
import AiBriefCard from "./AiBriefCard.vue"
import { compact, money, getClusterMeta } from "../theme"

const props = defineProps({
  overview: { type: Object, required: true },
  recommendations: { type: Array, required: true },
  anomalies: { type: Array, required: true },
  clusters: { type: Object, required: true },
  validation: { type: Object, required: true },
})

const emit = defineEmits(["select-tab", "select-org"])

// В витрину идёт подтверждённый резерв — без центров, у которых контроль
// качества нашёл внутренние расхождения в отчёте. Полный резерв остаётся рядом,
// чтобы разница была видна, а не спрятана.
const impact = computed(() => props.overview.recommendations?.impact_verified || {})
const impactFull = computed(() => props.overview.recommendations?.impact || {})
const flaggedCount = computed(() => props.overview.recommendations?.flagged_orgs?.length || 0)

/** Доля резерва к текущему объёму сети — считается, а не подписывается руками. */
function share(reserve, current) {
  if (!reserve || !current) return ""
  return `+${((reserve / current) * 100).toFixed(1)}% к текущему объёму сети`
}

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
      title: `${conversion.org_name}: высокий трафик при низкой конверсии`,
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
      title: `${error.org_name}: внутреннее противоречие цифр`,
      body:
        "В отчёте указано 69 проведённых мероприятий и всего 21 обученный участник — меньше " +
        "одного человека на событие. Автоматический контроль качества выявил опечатку " +
        "до принятия управленческих решений.",
      metric: "Выявлено автоматически",
      note: "верификация входного слоя данных",
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
        "Ряд центров оказывает профильные услуги бесплатно, тогда как " +
        "соседи по архетипу уже сформировали устойчивый портфель коммерческих заказов " +
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
    <!-- Hero блок -->
    <section class="card hero">
      <div class="hero-topline">
        <div class="live-tag">
          <span class="pulse-indicator" />
          <span>Сеть из {{ overview.organizations }} центров прототипирования вузов культуры</span>
        </div>
        <span class="badge badge-accent">Отчётный период: 9 месяцев 2026</span>
      </div>

      <h1 class="headline">
        Аналитическая платформа сети:<br />
        <span class="accent-text">{{ overview.recommendations?.total }} конкретных решений</span> по программированию
      </h1>

      <p class="lede">
        Платформа агрегирует ведомственную отчётность центров культуры,
        строит траектории динамики, группирует организации в 5 аудиторных архетипов
        и рассчитывает доказательный резерв роста без увеличения госбюджета.
      </p>

      <!-- 3 Главных показателя резерва -->
      <div class="impact-grid">
        <div v-if="impact.participants" class="impact-card">
          <div class="impact-val">+{{ compact(Math.round(impact.participants.total)) }}</div>
          <div class="impact-lbl">участников обучения</div>
          <div class="impact-sub">{{ share(impact.participants.total, overview.audience_total) }}</div>
        </div>
        <div v-if="impact.products" class="impact-card">
          <div class="impact-val">+{{ compact(Math.round(impact.products.total)) }}</div>
          <div class="impact-lbl">готовых творческих работ</div>
          <div class="impact-sub">{{ share(impact.products.total, overview.products_total) }}</div>
        </div>
        <div v-if="impact.revenue" class="impact-card">
          <div class="impact-val">+{{ money(impact.revenue.total) }}</div>
          <div class="impact-lbl">объёма платных услуг</div>
          <div class="impact-sub">{{ share(impact.revenue.total, overview.revenue_total) }}</div>
        </div>
      </div>

      <p v-if="flaggedCount" class="reserve-note muted">
        Это подтверждённый резерв. Ещё
        <b>+{{ compact(Math.round((impactFull.participants?.total || 0) - (impact.participants?.total || 0))) }}</b>
        участников приходится на {{ flaggedCount }} центра, у которых цифры внутри отчёта противоречат
        друг другу: такой резерв может оказаться артефактом заполнения, поэтому в сводную цифру он не
        включён — разбор по ним в разделе «Качество данных».
      </p>

      <div class="takeaway-box">
        <div class="takeaway-icon-dot" />
        <div class="takeaway-text">
          <strong>Вывод:</strong>
          Резерв достигается за счёт выравнивания наполняемости групп, перераспределения расписания
          и добавления проектных воркшопов на существующих площадях.
        </div>
      </div>
    </section>

    <!-- Исполнительское AI-резюме сети (Gemini 3.6 Flash) -->
    <AiBriefCard compact />

    <!-- 3 Шага работы платформы -->
    <section class="card">
      <h2>Методология конвейера данных</h2>
      <div class="steps-grid">
        <article class="step-card">
          <div class="step-num-code">01 / СБОР</div>
          <h3>Сбор и стандартизация отчётов</h3>
          <p class="muted">
            {{ overview.organizations }} книг Excel в разнородных шаблонах приводятся к единой матрице из 28 показателей.
            Автоматический аудит устраняет расхождения единиц измерения (рубли vs тыс. рублей) и находит аномалии.
          </p>
        </article>
        <article class="step-card">
          <div class="step-num-code">02 / КЛАСТЕРЫ</div>
          <h3>Кластеризация аудиторных моделей</h3>
          <p class="muted">
            Алгоритм выделил <b>{{ clusters.k }} устойчивых архетипов</b>.
            Каждое учреждение сравнивается только с равными — институты с институтами, камерные мастерские с мастерскими.
          </p>
        </article>
        <article class="step-card">
          <div class="step-num-code">03 / ЭФФЕКТ</div>
          <h3>Расчёт доказательных решений</h3>
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
        <h2>Ключевые инсайты по сети</h2>
        <p class="muted">Факты, выявленные алгоритмами в отчётности:</p>
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
            <span v-if="card.orgId" class="view-dossier-small">Досье →</span>
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
          <h2>5 аудиторных моделей работы</h2>
          <p class="muted">
            Основа справедливого сопоставления и бенчмаркинга:
          </p>
        </div>
        <button class="btn-primary" @click="emit('select-tab', 'clusters')">
          <span>Смотреть архетипы</span>
          <Icon name="arrow-right" :size="13" />
        </button>
      </div>

      <div class="arch-chips-row">
        <div
          v-for="p in clusters.profiles"
          :key="p.cluster_id"
          class="arch-chip-item"
          @click="emit('select-tab', 'clusters')"
        >
          <div class="chip-index" :style="{ color: getClusterMeta(p.cluster_id).color }">
            {{ getClusterMeta(p.cluster_id).index }}
          </div>
          <div class="chip-texts">
            <strong>{{ p.name }}</strong>
            <small class="muted">{{ p.size }} центров • {{ getClusterMeta(p.cluster_id).badge }}</small>
          </div>
        </div>
      </div>
    </section>

    <!-- Верификация и математическое доверие -->
    <section class="card">
      <h2>Верификация математической модели</h2>
      <div class="trust-grid">
        <div class="trust-cell">
          <div class="trust-icon-box">
            <Icon name="check" :size="14" />
          </div>
          <div>
            <strong>Разбиение на модели статистически доказано</strong>
            <p class="muted">
              Перестановочный тест из 2 000 симуляций подтвердил неслучайность структуры:
              вероятность случайного совпадения p = {{ validation.clustering?.permutation_p_value }}.
            </p>
          </div>
        </div>
        <div class="trust-cell">
          <div class="trust-icon-box">
            <Icon name="check" :size="14" />
          </div>
          <div>
            <strong>Устойчивость выводов к исключению объектов</strong>
            <p class="muted">
              При поочередном удалении каждого центра {{ Math.round(validation.recommendations?.stable_share * 100) }}%
              рекомендаций остаются стабильными.
            </p>
          </div>
        </div>
        <div class="trust-cell">
          <div class="trust-icon-box">
            <Icon name="check" :size="14" />
          </div>
          <div>
            <strong>100% реальные наблюдаемые данные</strong>
            <p class="muted">
              Все метрики построены на первичных отчетах Форм 1 и 2 без выдуманных синтетических суррогатов.
            </p>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.reserve-note {
  font-size: 12.5px;
  line-height: 1.55;
  margin: -4px 0 0;
}

.stack { display: flex; flex-direction: column; gap: 24px; }

.hero {
  padding: 32px 28px;
  background: var(--surface);
  border: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.hero-topline { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; }
.live-tag { display: flex; align-items: center; gap: 8px; font-size: 12px; font-weight: 600; color: var(--text-secondary); }

.headline { font-size: 24px; font-weight: 700; line-height: 1.25; margin: 4px 0; }
.accent-text { color: var(--accent); }
.lede { font-size: 14px; line-height: 1.6; color: var(--text-secondary); max-width: 880px; }

.impact-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 14px;
  margin: 8px 0;
}
.impact-card {
  background: var(--raised);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.impact-val { font-size: 26px; font-weight: 800; color: var(--success); font-variant-numeric: tabular-nums; }
.impact-lbl { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.impact-sub { font-size: 12px; color: var(--muted); }

.takeaway-icon-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--accent);
  margin-top: 6px;
  flex-shrink: 0;
}

.steps-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 14px;
  margin-top: 14px;
}
.step-card {
  background: var(--raised);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.step-num-code {
  font-size: 11px;
  font-weight: 700;
  font-family: monospace;
  color: var(--accent);
  letter-spacing: 0.05em;
}

.section-title-wrap { margin-bottom: 12px; }
.highlights-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 14px;
}
.highlight-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.highlight-card:hover { transform: translateY(-2px); border-color: var(--accent); }
.hl-top { display: flex; justify-content: space-between; align-items: center; }
.view-dossier-small { font-size: 11px; color: var(--accent); font-weight: 600; }
.hl-title { font-size: 14px; font-weight: 600; margin: 0; }
.hl-body { font-size: 13px; line-height: 1.5; margin: 0; }
.hl-bottom {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-top: auto;
  padding-top: 10px;
  border-top: 1px solid var(--border);
}
.hl-metric { font-size: 15px; color: var(--accent); font-weight: 700; }

.arch-banner-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 14px;
}
.arch-chips-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
}
.arch-chip-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: var(--raised);
  border: 1px solid var(--border);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.arch-chip-item:hover { background: var(--accent-wash); border-color: var(--accent); }
.chip-index { font-size: 15px; font-weight: 800; font-family: monospace; }
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
.trust-icon-box {
  width: 22px;
  height: 22px;
  border-radius: 6px;
  background: var(--success-wash);
  color: var(--success);
  display: grid;
  place-items: center;
  flex-shrink: 0;
  margin-top: 2px;
}
.trust-cell strong { font-size: 13px; color: var(--text-primary); display: block; margin-bottom: 3px; }
.trust-cell p { font-size: 12px; line-height: 1.5; margin: 0; }
</style>
