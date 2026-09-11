<script setup>
/**
 * Типы центров: человеческое описание найденных моделей работы.
 *
 * Раньше этот экран начинался с силуэта и ARI. Теперь он начинается с ответа
 * на вопрос «кто на кого похож и почему это важно», а статистика убрана в
 * раскрывающиеся блоки.
 */
import { computed } from 'vue'
import Disclosure from './Disclosure.vue'
import EChart from './EChart.vue'
import { axisStyle, baseOption, palette, plural } from '../theme'

const props = defineProps({
  clusters: { type: Object, required: true },
  validation: { type: Object, required: true },
  organizations: { type: Array, required: true },
})

const variance = computed(() => {
  const shown = props.clusters.explained_variance.slice(0, props.clusters.components)
  return Math.round(shown.reduce((a, b) => a + b, 0) * 100)
})

const byId = computed(() => {
  const map = {}
  for (const org of props.organizations) map[org.org_id] = org
  return map
})

/** Сводка типа в натуральных числах — понятнее, чем координаты центроида. */
function facts(profile) {
  const members = profile.members.map((id) => byId.value[id]).filter(Boolean)
  if (!members.length) return null
  const sum = (key) => members.reduce((acc, m) => acc + (m[key] || 0), 0)
  const audience = sum('audience_total')
  const formats = sum('supply_total')
  return {
    audience,
    formats,
    perEvent: formats ? Math.round(audience / formats) : 0,
    products: sum('products_total'),
  }
}

/**
 * Карта сети — малыми кратными.
 *
 * Пять категориальных цветов на одной диаграмме рассеяния не проходят проверку
 * различимости (в сравнении участвуют все пары цветов сразу). Поэтому каждый
 * тип получает свою панель: выделенный — акцентом, остальные — серым.
 */
function panelOption(clusterId) {
  const p = palette()
  const points = props.clusters.embedding
  const inside = points.filter((d) => d.cluster === clusterId)
  const outside = points.filter((d) => d.cluster !== clusterId)

  return {
    ...baseOption(),
    grid: { left: 4, right: 10, top: 10, bottom: 4, containLabel: true },
    tooltip: {
      ...baseOption().tooltip,
      formatter: (item) => `<b>${item.data[3]}</b><br/>аудитория: ${item.data[2]} чел.`,
    },
    xAxis: { type: 'value', ...axisStyle(), axisLabel: { show: false } },
    yAxis: { type: 'value', ...axisStyle(), axisLabel: { show: false } },
    series: [
      {
        name: 'остальные центры',
        type: 'scatter',
        symbolSize: 9,
        itemStyle: { color: p.dim, borderColor: p.surface, borderWidth: 2 },
        data: outside.map((d) => [d.pc1, d.pc2, d.audience_total, d.name]),
      },
      {
        name: 'этот тип',
        type: 'scatter',
        symbolSize: 13,
        itemStyle: { color: p.accent, borderColor: p.surface, borderWidth: 2 },
        data: inside.map((d) => [d.pc1, d.pc2, d.audience_total, d.name]),
      },
    ],
  }
}
</script>

<template>
  <div class="stack">
    <section class="card">
      <h2>Зачем делить сеть на типы</h2>
      <p class="lede">
        Музыкальную школу на двадцать человек и институт с аудиторией в полторы
        тысячи нельзя мерить одной линейкой. Система сама нашла
        <b>{{ plural(clusters.k, 'модель', 'модели', 'моделей') }} работы</b> — по тому, кого центр учит, насколько
        плотно с ним работает и что получает на выходе. Дальше каждый центр
        сравнивается только со своими.
      </p>
      <Disclosure label="Как именно считалось разбиение">
        <p>
          Одиннадцать признаков в четырёх блоках: состав аудитории по форматам
          (центрированное логарифмическое преобразование — доли на симплексе нельзя
          сравнивать напрямую), масштаб, глубина работы и отдача. После
          стандартизации — понижение размерности до {{ clusters.components }} главных
          компонент, покрывающих {{ variance }} % дисперсии.
        </p>
        <p>
          Число кластеров выбрано по совокупности силуэта, устойчивости на бутстрэпе,
          Calinski–Harabasz, Davies–Bouldin и баланса размеров, с правилом парсимонии.
          На {{ organizations.length }} наблюдениях силуэт растёт почти монотонно по k,
          поэтому диапазон ограничен сверху, а разбиения с кластером из одного объекта
          отбрасываются.
        </p>
        <p>
          k-средние и метод Уорда дали одинаковый результат
          (ARI&nbsp;=&nbsp;{{ clusters.agreement['kmeans~ward'] }}) — структура не
          артефакт конкретного алгоритма.
        </p>
      </Disclosure>
    </section>

    <section>
      <h2 class="section-title">{{ plural(clusters.k, 'тип', 'типа', 'типов') }} центров</h2>
      <div class="types">
        <article v-for="profile in clusters.profiles" :key="profile.cluster_id" class="card type">
          <header>
            <h3>{{ profile.name }}</h3>
            <span class="count">{{ plural(profile.size, 'центр', 'центра', 'центров') }}</span>
          </header>

          <ul class="traits">
            <li v-for="d in profile.distinctive" :key="d.feature">
              <span class="arrow" :class="d.z >= 0 ? 'up' : 'down'">{{ d.z >= 0 ? '↑' : '↓' }}</span>
              {{ d.label }}
            </li>
          </ul>

          <div v-if="facts(profile)" class="numbers">
            <div>
              <b>{{ facts(profile).audience.toLocaleString('ru-RU') }}</b>
              <span>человек</span>
            </div>
            <div>
              <b>{{ facts(profile).perEvent }}</b>
              <span>на мероприятие</span>
            </div>
            <div>
              <b>{{ facts(profile).products.toLocaleString('ru-RU') }}</b>
              <span>работ</span>
            </div>
          </div>

          <div class="members">
            <span v-for="name in profile.member_names" :key="name" class="member">{{ name }}</span>
          </div>
        </article>
      </div>
    </section>

    <section class="card">
      <h2>Карта сети</h2>
      <p class="lede">
        Каждая точка — центр. Чем ближе точки, тем более похоже центры работают с
        аудиторией. На каждой панели подсвечен свой тип, остальная сеть — серым.
      </p>
      <div class="panels">
        <figure v-for="profile in clusters.profiles" :key="profile.cluster_id">
          <figcaption>{{ profile.name }}</figcaption>
          <EChart :option="panelOption(profile.cluster_id)" height="160px" />
        </figure>
      </div>
      <Disclosure label="Почему панели, а не один график с пятью цветами">
        <p>
          На диаграмме рассеяния читателю приходится различать все пары цветов
          одновременно. Ни один набор из пяти оттенков не проходит контроль
          различимости сразу в светлой и тёмной теме — перебор всех сочетаний
          справочной палитры дал ноль подходящих. Разделение на панели решает задачу
          без потери информации: тип задаётся положением панели, а не оттенком.
        </p>
      </Disclosure>
    </section>
  </div>
</template>

<style scoped>
.stack { display: flex; flex-direction: column; gap: 22px; }
.lede { font-size: 14px; line-height: 1.6; color: var(--text-secondary); max-width: 74ch; margin-top: 8px; }
.lede b { color: var(--text-primary); }
.section-title { margin-bottom: 14px; }

.types { display: grid; grid-template-columns: repeat(auto-fit, minmax(290px, 1fr)); gap: 16px; }
.type header { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; }
.count { font-size: 12px; color: var(--muted); white-space: nowrap; }

.traits { list-style: none; margin: 14px 0 0; padding: 0; display: flex; flex-direction: column; gap: 7px; }
.traits li { font-size: 13px; color: var(--text-secondary); display: flex; gap: 8px; }
.arrow { font-weight: 700; font-size: 12px; }
.arrow.up { color: #0ca30c; }
.arrow.down { color: var(--muted); }

.numbers { display: flex; gap: 22px; margin-top: 18px; padding: 14px 0; border-top: 1px solid var(--border); border-bottom: 1px solid var(--border); }
.numbers div { display: flex; flex-direction: column; }
.numbers b { font-size: 17px; font-weight: 650; letter-spacing: -0.01em; }
.numbers span { font-size: 11px; color: var(--muted); margin-top: 1px; }

.members { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 14px; }
.member { font-size: 11px; padding: 3px 8px; border: 1px solid var(--border); border-radius: 6px; color: var(--text-secondary); }

.panels { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-top: 16px; }
figure { margin: 0; }
figcaption { font-size: 12px; font-weight: 600; margin-bottom: 2px; }
</style>
