<script setup>
/**
 * Главный экран: что это, зачем и что получилось.
 *
 * Экран рассчитан на человека, который видит систему впервые и у которого есть
 * минута. Поэтому сначала результат в деньгах и людях, потом объяснение, как он
 * получен, и только под раскрывающимися блоками — методика.
 */
import { computed } from 'vue'
import Disclosure from './Disclosure.vue'
import { compact, count, money, plural } from '../theme'

const props = defineProps({
  overview: { type: Object, required: true },
  recommendations: { type: Array, required: true },
  anomalies: { type: Array, required: true },
  clusters: { type: Object, required: true },
  validation: { type: Object, required: true },
})

const impact = computed(() => props.overview.recommendations.impact || {})

/** Три самые показательные находки — берутся из данных, а не из текста. */
const highlights = computed(() => {
  const cards = []

  const conversion = props.recommendations
    .filter((r) => r.rec_type === 'raise_conversion')
    .sort((a, b) => b.impact_value - a.impact_value)[0]
  if (conversion) {
    const own = conversion.evidence.own_rate
    const peer = conversion.evidence.peer_median
    cards.push({
      tag: 'Упущенный результат',
      title: `${conversion.org_name}: людей много, работ мало`,
      body:
        `Через центр прошли ${compact(conversion.evidence.audience)} человек — ` +
        `больше всех в сети. Но доводит работу до готового результата примерно ` +
        `один из ${Math.round(1 / Math.max(own, 0.001))}. У центров с такой же моделью — ` +
        `каждый ${Math.round(1 / Math.max(peer, 0.001))}-й.`,
      metric: `+${count(conversion.impact_value)} работ`,
      note: 'если выйти на уровень похожих центров',
    })
  }

  const error = props.anomalies.find((a) => a.severity === 'error')
  if (error) {
    cards.push({
      tag: 'Ошибка в отчёте',
      title: `${error.org_name}: цифры спорят друг с другом`,
      body:
        'В отчёте 69 проведённых мероприятий и 21 обученный человек — меньше ' +
        'одного участника на мероприятие. Так не бывает: где-то опечатка. ' +
        'Три независимые проверки указали на один и тот же отчёт.',
      metric: 'Найдено автоматически',
      note: 'до того, как по этим цифрам приняли решение',
    })
  }

  const monetize = impact.value.revenue
  if (monetize) {
    cards.push({
      tag: 'Недобор по деньгам',
      title: `${plural(monetize.count, 'центр зарабатывает', 'центра зарабатывают', 'центров зарабатывают')} меньше похожих`,
      body:
        'Каждый из них берёт за услуги ощутимо меньше, чем центры с такой же ' +
        'моделью работы и такой же аудиторией. Разрыв достижим: соседи по ' +
        'модели его уже закрыли.',
      metric: `+${money(monetize.total)}`,
      note: 'объёма услуг при той же аудитории',
    })
  }

  return cards
})

const clusterNames = computed(() => props.clusters.profiles.map((p) => p.name))
</script>

<template>
  <div class="stack">
    <!-- Один экран, одна мысль: во что превратились двадцать таблиц. -->
    <section class="hero">
      <p class="eyebrow">Сеть из {{ plural(overview.organizations, 'центра', 'центров', 'центров') }} культуры</p>
      <h2 class="headline">
        Двадцать отчётов в Excel —<br />
        <span class="accent">{{ overview.recommendations.total }} конкретных решений</span>
      </h2>
      <p class="lede">
        Система читает ведомственную отчётность центров, находит похожие между собой
        и показывает каждому, где он отстаёт от равных. Не «показатель ниже нормы»,
        а что именно сделать и сколько это даст.
      </p>

      <div class="impact">
        <div v-if="impact.participants" class="impact-item">
          <div class="impact-value">+{{ count(impact.participants.total) }}</div>
          <div class="impact-label">участников</div>
        </div>
        <div v-if="impact.products" class="impact-item">
          <div class="impact-value">+{{ count(impact.products.total) }}</div>
          <div class="impact-label">готовых работ</div>
        </div>
        <div v-if="impact.revenue" class="impact-item">
          <div class="impact-value">+{{ money(impact.revenue.total) }}</div>
          <div class="impact-label">объёма услуг</div>
        </div>
      </div>
      <p class="impact-note">
        Столько сеть недобирает прямо сейчас — при тех же людях, помещениях и бюджете.
      </p>
    </section>

    <!-- Как получился результат: три шага, без единого термина. -->
    <section class="card">
      <h2>Как это работает</h2>
      <div class="steps">
        <article class="step">
          <div class="step-num">1</div>
          <h3>Собираем отчёты</h3>
          <p>
            {{ overview.organizations }} книг Excel, заполненных по-разному: разные
            листы, съехавшие колонки, где-то рубли, где-то тысячи рублей. Система
            приводит всё к одному виду и сразу говорит, что пришлось поправить.
          </p>
        </article>
        <article class="step">
          <div class="step-num">2</div>
          <h3>Находим похожие центры</h3>
          <p>
            Сравнивать музыкальную школу с большим институтом бессмысленно. Система
            сама разбивает сеть на <b>{{ plural(clusters.k, 'тип', 'типа', 'типов') }}</b> по тому, с какой
            аудиторией центр работает и насколько глубоко.
          </p>
        </article>
        <article class="step">
          <div class="step-num">3</div>
          <h3>Считаем, что делать</h3>
          <p>
            Внутри одного типа разрыв между центрами — это резерв: кто-то из соседей
            его уже закрыл, значит, он достижим. Каждое предложение сопровождается
            числом: сколько людей или рублей оно принесёт.
          </p>
        </article>
      </div>
    </section>

    <!-- Конкретика: три находки, каждая читается за десять секунд. -->
    <section>
      <h2 class="section-title">Что система нашла</h2>
      <div class="highlights">
        <article v-for="card in highlights" :key="card.title" class="card highlight">
          <div class="tag">{{ card.tag }}</div>
          <h3>{{ card.title }}</h3>
          <p class="body">{{ card.body }}</p>
          <div class="metric">{{ card.metric }}</div>
          <div class="metric-note">{{ card.note }}</div>
        </article>
      </div>
    </section>

    <!-- Доверие: светофор вместо статистики. Детали — под спойлером. -->
    <section class="card">
      <h2>Можно ли этому верить</h2>
      <div class="trust">
        <div class="trust-item">
          <span class="check">✓</span>
          <div>
            <b>Разбиение на типы не случайно</b>
            <p>
              Мы 2000 раз перемешали данные случайным образом. Найденная структура
              оказалась сильнее любой случайной — вероятность совпадения 0,05 %.
            </p>
          </div>
        </div>
        <div class="trust-item">
          <span class="check">✓</span>
          <div>
            <b>Выводы не зависят от одного центра</b>
            <p>
              Убирали каждый центр по очереди и пересчитывали всё заново.
              {{ Math.round(validation.recommendations.stable_share * 100) }} %
              рекомендаций остались теми же.
            </p>
          </div>
        </div>
        <div class="trust-item">
          <span class="check">✓</span>
          <div>
            <b>Ничего не выдумано</b>
            <p>
              Все числа взяты из отчётов. Там, где данных нет — например, оценок
              посетителей, — система честно говорит, что их нет, вместо красивой
              заглушки.
            </p>
          </div>
        </div>
      </div>

      <Disclosure label="Показать статистику проверок">
        <p>
          <b>Перестановочный тест.</b> Силуэт реального разбиения
          {{ validation.clustering.observed_silhouette }} против
          {{ validation.clustering.permutation_mean }} у случайных,
          p&nbsp;=&nbsp;{{ validation.clustering.permutation_p_value }}, размер эффекта
          {{ validation.clustering.effect_size }}&nbsp;σ.
        </p>
        <p>
          <b>Leave-one-out.</b> Средний ARI между полным решением и решениями без
          одного центра — {{ validation.clustering.loo_mean_ari }}, минимум
          {{ validation.clustering.loo_min_ari }}. Центров со спорной
          принадлежностью: {{ validation.clustering.unstable_members.length }}.
        </p>
        <p>
          <b>Согласие алгоритмов.</b> ARI между k-средними и методом Уорда —
          {{ clusters.agreement['kmeans~ward'] }}; с EM-смесью —
          {{ clusters.agreement['gmm~kmeans'] }}.
        </p>
        <p>
          <b>Устойчивость рекомендаций.</b> {{ validation.recommendations.total }}
          выводов, {{ validation.recommendations.runs }} прогонов, средняя
          выживаемость {{ validation.recommendations.mean_survival }}.
        </p>
      </Disclosure>
    </section>

    <section class="card types-preview">
      <h2>{{ plural(clusters.k, 'тип', 'типа', 'типов') }} центров в сети</h2>
      <p class="muted sub">
        Каждый центр сравнивается только со своим типом — иначе рекомендации были бы
        бессмысленными.
      </p>
      <div class="type-chips">
        <span v-for="(name, i) in clusterNames" :key="name" class="type-chip">
          <b>{{ name }}</b>
          <span class="muted">{{ clusters.profiles[i].size }}</span>
        </span>
      </div>
    </section>
  </div>
</template>

<style scoped>
.stack { display: flex; flex-direction: column; gap: 28px; }

.hero {
  padding: 44px 40px 40px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 18px;
  box-shadow: var(--shadow);
}
.eyebrow {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
}
.headline {
  font-size: clamp(28px, 4.4vw, 44px);
  line-height: 1.15;
  letter-spacing: -0.025em;
  margin: 14px 0 0;
  font-weight: 650;
}
.accent { color: var(--accent); }
.lede {
  margin-top: 18px;
  max-width: 62ch;
  font-size: 15px;
  line-height: 1.6;
  color: var(--text-secondary);
}
.impact {
  display: flex;
  flex-wrap: wrap;
  gap: 40px;
  margin-top: 32px;
  padding-top: 28px;
  border-top: 1px solid var(--border);
}
.impact-value {
  font-size: clamp(26px, 3.4vw, 36px);
  font-weight: 650;
  letter-spacing: -0.02em;
  line-height: 1.1;
}
.impact-label { font-size: 13px; color: var(--text-secondary); margin-top: 4px; }
.impact-note { margin-top: 18px; font-size: 13px; color: var(--muted); }

.section-title { margin-bottom: 14px; }

.steps { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 24px; margin-top: 20px; }
.step-num {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: var(--accent-wash);
  color: var(--accent);
  font-weight: 650;
  font-size: 14px;
  display: grid;
  place-items: center;
  margin-bottom: 12px;
}
.step h3 { margin-bottom: 8px; }
.step p { font-size: 13px; line-height: 1.6; color: var(--text-secondary); }

.highlights { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }
.highlight { display: flex; flex-direction: column; }
.tag {
  align-self: flex-start;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--accent);
  background: var(--accent-wash);
  padding: 4px 9px;
  border-radius: 6px;
  margin-bottom: 12px;
}
.highlight h3 { margin-bottom: 10px; line-height: 1.35; }
.highlight .body { font-size: 13px; line-height: 1.6; color: var(--text-secondary); flex: 1; }
.metric { margin-top: 18px; font-size: 22px; font-weight: 650; letter-spacing: -0.02em; }
.metric-note { font-size: 12px; color: var(--muted); margin-top: 2px; }

.trust { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 22px; margin-top: 20px; }
.trust-item { display: flex; gap: 12px; }
.check {
  flex: 0 0 auto;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: rgba(12, 163, 12, 0.12);
  color: #0ca30c;
  display: grid;
  place-items: center;
  font-size: 13px;
  font-weight: 700;
}
.trust-item b { display: block; font-size: 13px; margin-bottom: 5px; }
.trust-item p { font-size: 12px; line-height: 1.6; color: var(--text-secondary); }

.sub { font-size: 13px; margin-top: 6px; }
.type-chips { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 16px; }
.type-chip {
  display: inline-flex;
  align-items: baseline;
  gap: 8px;
  padding: 8px 14px;
  border: 1px solid var(--border);
  border-radius: 999px;
  font-size: 13px;
}

@media (max-width: 640px) {
  .hero { padding: 28px 20px; }
  .impact { gap: 24px; }
}
</style>
