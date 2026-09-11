<script setup>
/** Обзор сети: сводные показатели, состав аудитории, исполнение плана. */
import { computed } from 'vue'
import EChart from './EChart.vue'
import ChartGuide from './ChartGuide.vue'
import StatTile from './StatTile.vue'
import { axisStyle, baseOption, compact, money, palette, PLAN_STATUS } from '../theme'

const props = defineProps({
  overview: { type: Object, required: true },
  organizations: { type: Array, required: true },
  plan: { type: Array, required: true },
  channels: { type: Array, required: true },
})

const sorted = computed(() =>
  [...props.organizations].sort((a, b) => b.audience_total - a.audience_total),
)

/** Состав аудитории по форматам: составные столбики, зазор в цвет фона. */
const mixOption = computed(() => {
  const p = palette()
  const rows = sorted.value
  return {
    ...baseOption(),
    legend: {
      top: 0,
      left: 0,
      itemWidth: 10,
      itemHeight: 10,
      itemGap: 16,
      textStyle: { color: p.textSecondary, fontSize: 12 },
    },
    grid: { left: 8, right: 16, top: 36, bottom: 8, containLabel: true },
    tooltip: { ...baseOption().tooltip, trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: { type: 'value', ...axisStyle(), name: 'человек', nameTextStyle: { color: p.muted, fontSize: 11 } },
    yAxis: {
      type: 'category',
      data: rows.map((r) => r.short_name),
      ...axisStyle(),
      splitLine: { show: false },
      inverse: true,
    },
    series: props.channels.map((channel, index) => ({
      name: channel.label,
      type: 'bar',
      stack: 'audience',
      barMaxWidth: 18,
      // Зазор в цвет подложки разделяет сегменты вместо обводки.
      itemStyle: { color: p.series[index], borderColor: p.surface, borderWidth: 2 },
      data: rows.map((r) => r[`audience_${channel.key}`]),
    })),
  }
})

/** Исполнение годовой цели: одна серия, опорная линия на 100 %. */
const planOption = computed(() => {
  const p = palette()
  const rows = [...props.plan]
    .filter((r) => r.status !== 'без базы')
    .sort((a, b) => a.completion - b.completion)
  return {
    ...baseOption(),
    grid: { left: 8, right: 40, top: 16, bottom: 8, containLabel: true },
    tooltip: {
      ...baseOption().tooltip,
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      valueFormatter: (v) => `${Math.round(v * 100)} %`,
    },
    xAxis: {
      type: 'value',
      ...axisStyle(),
      axisLabel: { color: p.muted, fontSize: 11, formatter: (v) => `${Math.round(v * 100)} %` },
    },
    yAxis: {
      type: 'category',
      data: rows.map((r) => r.short_name),
      ...axisStyle(),
      splitLine: { show: false },
      inverse: true,
    },
    series: [
      {
        name: 'Выполнение цели года',
        type: 'bar',
        barMaxWidth: 16,
        itemStyle: { color: p.accent, borderRadius: [0, 4, 4, 0] },
        data: rows.map((r) => r.completion),
        markLine: {
          silent: true,
          symbol: 'none',
          label: { formatter: 'цель', color: p.muted, fontSize: 11 },
          lineStyle: { color: p.axis, width: 1, type: 'solid' },
          data: [{ xAxis: 1 }],
        },
      },
    ],
  }
})

const planCounts = computed(() => Object.entries(props.overview.plan_status || {}))
</script>

<template>
  <div class="stack">
    <div class="tiles">
      <StatTile
        label="Аудитория сети за отчётный период"
        :value="compact(overview.audience_total)"
        note="человек прошли обучение на мероприятиях центров"
        hero
      />
      <StatTile label="Проведено форматов" :value="compact(overview.formats_total)" note="модули, мастер-классы, ПК и переподготовка" />
      <StatTile label="Создано творческих продуктов" :value="compact(overview.products_total)" :note="`${overview.median_product_rate} продукта на участника — медиана сети`" />
      <StatTile label="Объём оказанных услуг" :value="money(overview.revenue_total)" note="по всем видам деятельности" />
      <StatTile label="Публикаций в СМИ" :value="compact(overview.publications_total)" :note="`${overview.federal_events_total} выходов на федеральные площадки`" />
      <StatTile
        label="План года под угрозой"
        :value="`${overview.plan_at_risk} из ${overview.organizations}`"
        note="центров не выходят на цель при текущем темпе"
      />
    </div>

    <div class="card">
      <h2>Состав аудитории по форматам</h2>
      <p class="muted sub">
        Здесь видно, сколько человек обучалось в каждом центре и какие форматы обучения они посещали.
      </p>
      <ChartGuide>
        <li><strong>Одна полоса — один центр.</strong> Чем она длиннее, тем больше суммарная аудитория. Сверху — центры с самой большой аудиторией.</li>
        <li><strong>Цветные части — форматы обучения.</strong> Их названия указаны над графиком. Длина каждой части показывает число обученных в этом формате; вместе части дают общий итог центра. ПК — повышение квалификации.</li>
        <li><strong>Пример:</strong> если две части полосы соответствуют 200 и 300 людям, общий итог — 500. Шкала по горизонтали показывает людей, а не проценты.</li>
        <li>Наведите на полосу, чтобы увидеть точные числа. Нажатие на название формата в легенде скрывает или возвращает его — при скрытии длина полос показывает только оставшиеся форматы.</li>
      </ChartGuide>
      <EChart :option="mixOption" height="520px" />
    </div>

    <div class="card">
      <h2>Исполнение годовой цели по числу мероприятий</h2>
      <p class="muted sub">
        Цель — прирост на 10 % к предыдущему году (строка 1 Формы 1). Отчёт охватывает девять
        месяцев, поэтому значение ниже 75 % означает отставание от равномерного темпа.
      </p>
      <ChartGuide>
        <li><strong>Одна полоса — один центр.</strong> Её длина показывает, какая часть годового плана мероприятий уже выполнена. Сверху — центры с наименьшим процентом выполнения.</li>
        <li><strong>100 % — годовой план выполнен.</strong> Это отмечено линией «цель». Например, 50 % означает, что проведена половина запланированных мероприятий, а 120 % — план превышен на 20 %.</li>
        <li><strong>За девять месяцев ориентир — 75 %.</strong> Ниже — отставание, если проводить мероприятия равномерно весь год. Значение от 75 до 100 % ещё не означает выполнения всего годового плана.</li>
        <li>Наведите на полосу, чтобы увидеть процент. Центры со статусом «без базы» не показаны: для сравнения нет данных за предыдущий год.</li>
      </ChartGuide>
      <div class="legend-row">
        <span v-for="[status, count] in planCounts" :key="status" class="chip">
          <span :style="{ color: PLAN_STATUS[status]?.color }">{{ PLAN_STATUS[status]?.icon }}</span>
          {{ status }} — {{ count }}
        </span>
      </div>
      <EChart :option="planOption" height="440px" />
    </div>
  </div>
</template>

<style scoped>
.stack { display: flex; flex-direction: column; gap: 20px; }
.tiles {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 14px;
}
.sub { font-size: 13px; margin-top: 6px; max-width: 76ch; }
.legend-row { display: flex; flex-wrap: wrap; gap: 14px; margin: 14px 0 4px; }
.chip { font-size: 12px; color: var(--text-secondary); display: inline-flex; gap: 6px; align-items: center; }
</style>
