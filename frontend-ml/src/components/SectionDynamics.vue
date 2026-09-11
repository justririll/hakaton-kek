<script setup>
/**
 * Раздел «Посещаемость & Динамика»:
 * Графики динамики по кварталам, сравнение 2025 vs 2026, структура форматов и контроль плана.
 */
import { computed, ref } from "vue"
import EChart from "./EChart.vue"
import StatTile from "./StatTile.vue"
import { axisStyle, baseOption, compact, money, palette, PLAN_STATUS, percent } from "../theme"

const props = defineProps({
  overview: { type: Object, required: true },
  organizations: { type: Array, required: true },
  plan: { type: Array, required: true },
  channels: { type: Array, required: true },
})

const emit = defineEmits(["select-org"])

// Активная метрика для графика динамики
const activeMetric = ref("audience")

const sortedOrgs = computed(() =>
  [...props.organizations].sort((a, b) => b.audience_total - a.audience_total),
)

/** Форматирование значения по показателю. */
const FORMATTERS = {
  audience: (v) => compact(Math.round(v)) + " чел.",
  formats: (v) => compact(Math.round(v)) + " ед.",
  products: (v) => compact(Math.round(v)) + " шт.",
  revenue: (v) => money(v),
}

/**
 * Динамика приходит из API и содержит ровно то, что есть в отчётности.
 * База 2025 года заполнена только там, где её заполнили организации; где её
 * нет — показываем это прямо, а не подставляем правдоподобное число.
 *
 * Где база есть, и база, и факт берутся по одному и тому же кругу центров
 * (`fact_comparable`), иначе сравнивались бы разные совокупности.
 */
const metrics = computed(() => {
  const out = {}
  for (const row of props.overview?.dynamics || []) {
    const months = row.reported_months || 9
    const hasBase = row.baseline_2025 !== null && row.baseline_2025 !== undefined
    const factPoint = hasBase ? row.fact_comparable : row.fact_ytd
    out[row.key] = {
      ...row,
      hasBase,
      factPoint,
      forecastPoint: factPoint * (12 / months),
      formatter: FORMATTERS[row.key] || ((v) => compact(v)),
    }
  }
  return out
})

const activeCfg = computed(() => metrics.value[activeMetric.value] || null)

// Мероприятия — единственный показатель с базой 2025 года, на нём строится вывод раздела.
const formatsCfg = computed(() => metrics.value.formats || null)

/** Подпись темпа: в годовом выражении либо честное «сравнивать не с чем». */
function growthText(cfg) {
  if (!cfg) return ""
  if (!cfg.hasBase) return "базы 2025 года в отчётности нет"
  const sign = cfg.growth_year >= 0 ? "+" : ""
  return `${sign}${(cfg.growth_year * 100).toFixed(1)}% к 2025 г. (в годовом выражении)`
}

const growthLabel = computed(() => growthText(activeCfg.value))

/** График динамики: факт 2025 → факт отчётного периода → проекция года. */
const trajectoryChartOption = computed(() => {
  const p = palette()
  const cfg = activeCfg.value
  if (!cfg) return baseOption()

  const factLabel = `${cfg.reported_months} мес. 2026 (факт)`
  const axis = cfg.hasBase
    ? ["2025 (факт года)", factLabel, "2026 (проекция года)"]
    : [factLabel, "2026 (проекция года)"]

  const factSeries = cfg.hasBase ? [cfg.baseline_2025, cfg.factPoint, null] : [cfg.factPoint, null]
  const forecastSeries = cfg.hasBase
    ? [null, cfg.factPoint, cfg.forecastPoint]
    : [cfg.factPoint, cfg.forecastPoint]

  const pointLabel = {
    show: true,
    position: "top",
    color: p.textSecondary,
    fontSize: 11,
    fontWeight: 600,
    formatter: ({ value }) => (value === null || value === undefined ? "" : cfg.formatter(value)),
  }

  const factLine = {
    name: "Факт отчётности",
    type: "line",
    smooth: false,
    symbolSize: 9,
    label: pointLabel,
    itemStyle: { color: p.accent },
    lineStyle: { width: 2.5, color: p.accent },
    areaStyle: {
      color: {
        type: "linear",
        x: 0,
        y: 0,
        x2: 0,
        y2: 1,
        colorStops: [
          { offset: 0, color: p.accent + "40" },
          { offset: 1, color: p.accent + "05" },
        ],
      },
    },
    data: factSeries,
  }

  // Цель года задана Формой 1 только для числа мероприятий; для остальных
  // показателей планового значения не существует и линии цели быть не должно.
  if (cfg.target_2026) {
    factLine.markLine = {
      silent: true,
      symbol: "none",
      label: {
        formatter: `Цель года: ${cfg.formatter(cfg.target_2026)}`,
        position: "insideEndTop",
        color: p.muted,
        fontSize: 11,
      },
      lineStyle: { color: "#f59e0b", width: 1.5, type: "dashed" },
      data: [{ yAxis: cfg.target_2026 }],
    }
  }

  return {
    ...baseOption(),
    tooltip: {
      ...baseOption().tooltip,
      trigger: "axis",
      formatter: (items) => {
        let res = `<b>${items[0].name}</b><br/>`
        for (const it of items) {
          if (it.value !== null && it.value !== undefined) {
            res += `<span style="color:${it.color}">●</span> ${it.seriesName}: <b>${cfg.formatter(it.value)}</b><br/>`
          }
        }
        return res
      },
    },
    legend: {
      top: 0,
      left: "center",
      itemWidth: 10,
      itemHeight: 10,
      itemGap: 10,
      textStyle: { color: p.textSecondary, fontSize: 10 },
    },
    // Точек мало и boundaryGap выключен, поэтому крайние подписи упираются в
    // границы области построения — отсюда увеличенные поля слева и справа.
    grid: { left: 76, right: 62, top: 56, bottom: 15, containLabel: true },
    xAxis: {
      type: "category",
      boundaryGap: false,
      data: axis,
      ...axisStyle(),
      axisLabel: { color: p.muted, fontSize: 11, hideOverlap: false },
    },
    yAxis: {
      type: "value",
      ...axisStyle(),
      axisLabel: {
        color: p.muted,
        fontSize: 11,
        formatter: (v) => (cfg.unit === "₽" ? money(v) : compact(v)),
      },
    },
    series: [
      factLine,
      {
        name: "Проекция года по текущему темпу",
        type: "line",
        smooth: false,
        symbol: "circle",
        symbolSize: 9,
        // Проекция начинается в той же точке, что и факт: подписывать её дважды
        // не нужно, поэтому у пунктира подписан только конец.
        label: {
          ...pointLabel,
          position: "bottom",
          formatter: ({ value, dataIndex }) =>
            dataIndex === forecastSeries.length - 1 && value !== null ? cfg.formatter(value) : "",
        },
        itemStyle: { color: "#10b981" },
        lineStyle: { width: 2, type: "dashed", color: "#10b981" },
        data: forecastSeries,
      },
    ],
  }
})


/** Состав аудитории по форматам (составные бары) */
const mixOption = computed(() => {
  const p = palette()
  const rows = sortedOrgs.value
  return {
    ...baseOption(),
    legend: {
      top: 0,
      left: "center",
      itemWidth: 9,
      itemHeight: 9,
      itemGap: 10,
      textStyle: { color: p.textSecondary, fontSize: 10 },
    },
    grid: { left: 4, right: 16, top: 54, bottom: 8, containLabel: true },
    tooltip: { ...baseOption().tooltip, trigger: "axis", axisPointer: { type: "shadow" } },
    xAxis: { type: "value", ...axisStyle(), name: "чел.", nameTextStyle: { color: p.muted, fontSize: 10 } },
    yAxis: {
      type: "category",
      data: rows.map((r) => r.short_name),
      ...axisStyle(),
      splitLine: { show: false },
      inverse: true,
      axisLabel: {
        color: p.textSecondary,
        fontSize: 10,
        width: 85,
        overflow: "truncate",
        interval: 0,
      },
    },
    series: props.channels.map((channel, index) => ({
      name: channel.label,
      type: "bar",
      stack: "audience",
      barMaxWidth: 15,
      itemStyle: { color: p.series[index % p.series.length], borderColor: p.surface, borderWidth: 1.5 },
      data: rows.map((r) => r[`audience_${channel.key}`]),
    })),
  }
})

/** Доли форматов в сети (Donut Chart) */
const donutFormatOption = computed(() => {
  const p = palette()
  const totalByChannel = props.channels.map((ch, idx) => {
    const sum = props.organizations.reduce((acc, o) => acc + (o[`audience_${ch.key}`] || 0), 0)
    return {
      name: ch.label,
      value: sum,
      itemStyle: { color: p.series[idx % p.series.length] },
    }
  })

  return {
    ...baseOption(),
    tooltip: { trigger: "item", formatter: "{b}: <b>{c} чел.</b> ({d}%)" },
    legend: {
      bottom: 0,
      left: "center",
      itemWidth: 8,
      itemHeight: 8,
      itemGap: 8,
      textStyle: { color: p.textSecondary, fontSize: 10 },
    },
    series: [
      {
        name: "Формат",
        type: "pie",
        radius: ["35%", "55%"],
        center: ["50%", "38%"],
        avoidLabelOverlap: true,
        itemStyle: { borderRadius: 5, borderColor: p.surface, borderWidth: 2 },
        label: {
          show: true,
          position: "inside",
          formatter: "{d}%",
          fontSize: 10,
          color: "#ffffff",
          fontWeight: "600",
        },
        data: totalByChannel,
      },
    ],
  }
})

/** Исполнение годовой цели по организациям */
const planOption = computed(() => {
  const p = palette()
  const rows = [...props.plan]
    .filter((r) => r.status !== "без базы")
    .sort((a, b) => a.completion - b.completion)

  return {
    ...baseOption(),
    grid: { left: 4, right: 30, top: 16, bottom: 8, containLabel: true },
    tooltip: {
      ...baseOption().tooltip,
      trigger: "axis",
      axisPointer: { type: "shadow" },
      formatter: (items) => {
        const item = items[0]
        const row = rows[item.dataIndex]
        return `<b>${row.short_name}</b><br/>
                Выполнение плана: <b>${Math.round(row.completion * 100)}%</b><br/>
                Факт: <b>${row.fact_ytd} ед.</b> из <b>${row.target_2026} ед.</b><br/>
                Статус: <b>${row.status}</b>`
      },
    },
    xAxis: {
      type: "value",
      ...axisStyle(),
      axisLabel: { color: p.muted, fontSize: 10, formatter: (v) => `${Math.round(v * 100)}%` },
    },
    yAxis: {
      type: "category",
      data: rows.map((r) => r.short_name),
      ...axisStyle(),
      splitLine: { show: false },
      inverse: true,
      axisLabel: {
        color: p.textSecondary,
        fontSize: 10,
        width: 85,
        overflow: "truncate",
        interval: 0,
      },
    },
    series: [
      {
        name: "Выполнение цели года",
        type: "bar",
        barMaxWidth: 14,
        itemStyle: {
          color: (params) => {
            const row = rows[params.dataIndex]
            return PLAN_STATUS[row.status]?.color || p.accent
          },
          borderRadius: [0, 4, 4, 0],
        },
        data: rows.map((r) => r.completion),
        markLine: {
          silent: true,
          symbol: "none",
          label: { formatter: "100% норма", color: p.muted, fontSize: 11 },
          lineStyle: { color: p.axis, width: 1.5, type: "solid" },
          data: [{ xAxis: 1 }],
        },
      },
    ],
  }
})
</script>

<template>
  <div class="stack">
    <!-- Понятное объяснение -->
    <div class="takeaway-box">
      <div class="takeaway-text">
        <strong>Вывод раздела:</strong>
        <template v-if="formatsCfg">
          Единственный показатель, у которого в отчётности есть база 2025 года, — число мероприятий:
          <b>{{ formatsCfg.fact_comparable }} ед.</b> за {{ formatsCfg.reported_months }} месяцев против
          <b>{{ formatsCfg.baseline_2025 }} ед.</b> за весь 2025 год по одному и тому же кругу
          {{ formatsCfg.baseline_orgs }} центров — это {{ growthText(formatsCfg) }}.
          Проекция года — <b>{{ formatsCfg.formatter(formatsCfg.forecastPoint) }}</b>
          при годовой цели <b>{{ formatsCfg.formatter(formatsCfg.target_2026) }}</b>,
          заданной строкой 1 Формы 1: сеть выходит на план впритык.
        </template>
        При этом <b>{{ overview.plan_at_risk }} из {{ overview.organizations }} учреждений</b> прогнозно
        не добирают собственную цель года и требуют адресной поддержки в IV квартале.
        По посещаемости, арт-продуктам и платным услугам базы 2025 года в отчётности нет —
        темп к прошлому году по ним не считается.
      </div>
    </div>

    <!-- Ключевые метрики динамики -->
    <div class="tiles-grid">
      <StatTile
        label="Посещаемость за 9 мес."
        :value="compact(overview.audience_total)"
        note="человек за отчётный период (базы 2025 г. в отчётности нет)"
        hero
      />
      <StatTile
        label="Проведено мероприятий"
        :value="compact(overview.formats_total)"
        note="курсы, мастер-классы, интенсивы"
      />
      <StatTile
        label="Готовых арт-продуктов"
        :value="compact(overview.products_total)"
        :note="`в среднем ${overview.median_product_rate} работ на человека`"
      />
      <StatTile
        label="Заработано на услугах"
        :value="money(overview.revenue_total)"
        note="доход от прототипирования и ДПО"
      />
      <StatTile
        label="Средняя группа"
        :value="`${overview.median_audience_per_format} чел.`"
        note="наполняемость на одном мероприятии"
      />
      <StatTile
        label="План года под риском"
        :value="`${overview.plan_at_risk} из ${overview.organizations}`"
        note="прогноз года ниже цели Формы 1"
      />
    </div>

    <!-- Интерактивный график динамики (Тренды) -->
    <div class="card">
      <div class="section-header-row">
        <div>
          <h2>Динамика показателей сети</h2>
          <p class="muted sub">
            Отчётность даёт один срез за {{ activeCfg?.reported_months || 9 }} месяцев и базу 2025 года там,
            где организации её заполнили. Промежуточных кварталов в формах нет, поэтому на графике только
            наблюдаемые точки и проекция года по текущему темпу.
          </p>
        </div>
        <div class="metric-tabs">
          <button
            v-for="(cfg, key) in metrics"
            :key="key"
            :class="{ active: activeMetric === key }"
            @click="activeMetric = key"
          >
            {{ cfg.label }}
          </button>
        </div>
      </div>

      <div v-if="activeCfg" class="metric-meta-bar">
        <span class="badge" :class="activeCfg.hasBase ? 'badge-accent' : 'badge-neutral'">{{ growthLabel }}</span>
        <span class="muted">
          Факт {{ activeCfg.reported_months }} месяцев: <b>{{ activeCfg.formatter(activeCfg.fact_ytd) }}</b>
        </span>
        <span class="muted">
          Проекция года: <b>{{ activeCfg.formatter(activeCfg.run_rate_year) }}</b>
        </span>
        <span v-if="activeCfg.hasBase" class="muted">
          На графике — сопоставимый круг
          <b>{{ activeCfg.baseline_orgs }} из {{ overview.organizations }}</b> центров:
          <b>{{ activeCfg.formatter(activeCfg.fact_comparable) }}</b>
        </span>
      </div>

      <EChart :option="trajectoryChartOption" height="320px" />
    </div>

    <!-- Две колонки: Состав аудитории и Доли форматов -->
    <div class="two-col-grid">
      <div class="card">
        <h2>Посещаемость по форматам обучения</h2>
        <p class="muted sub">
          Распределение аудитории каждого центра по 4 каналам (курсы, мастер-классы, повышение квалификации, переподготовка).
        </p>
        <EChart :option="mixOption" height="480px" />
      </div>

      <div class="card flex-card">
        <h2>Доли форматов в аудитории сети</h2>
        <p class="muted sub">
          Какие форматы привлекают наибольший объем участников.
        </p>
        <EChart :option="donutFormatOption" height="260px" />

        <div class="format-notes">
          <div class="format-item">
            <span class="format-dot" style="background: var(--accent);" />
            <div>
              <strong>Курсы (модули):</strong>
              <p class="muted">Основной драйвер готовых авторских работ и долгосрочных резидентов.</p>
            </div>
          </div>
          <div class="format-item">
            <span class="format-dot" style="background: #eb6834;" />
            <div>
              <strong>Мастер-классы:</strong>
              <p class="muted">Максимальный поток посетителей при минимальном пороге входа.</p>
            </div>
          </div>
          <div class="format-item">
            <span class="format-dot" style="background: #1baf7a;" />
            <div>
              <strong>Повышение квалификации (ДПО):</strong>
              <p class="muted">Ключевой источник платных образовательных услуг центров.</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Исполнение годового плана госпрограммы -->
    <div class="card">
      <div class="section-header-row">
        <div>
          <h2>Выполнение годового плана по организациям</h2>
          <p class="muted sub">
            Цель — прирост числа мероприятий к 2025 году из строки 1 Формы 1. Статус определяется не
            текущим процентом, а прогнозом года по нынешнему темпу: выше цели — опережение, ниже 85 % от
            неё — срыв.
          </p>
        </div>
        <div class="status-legend">
          <span class="badge badge-good">Опережение / В графике</span>
          <span class="badge badge-warning">Зона риска</span>
          <span class="badge badge-danger">Срыв плана</span>
        </div>
      </div>
      <EChart :option="planOption" height="480px" />
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

.section-header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 14px;
}
.metric-tabs { display: flex; flex-wrap: wrap; gap: 4px; }
.metric-meta-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
  font-size: 13px;
  margin-bottom: 12px;
  padding: 8px 12px;
  background: var(--raised);
  border-radius: 8px;
}

.two-col-grid > * { min-width: 0; }
.two-col-grid {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 20px;
}
@media (max-width: 900px) {
  .two-col-grid { grid-template-columns: 1fr; }
}

.flex-card { display: flex; flex-direction: column; }
.format-notes {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 14px;
  border-top: 1px solid var(--border);
  padding-top: 14px;
}
.format-item { display: flex; align-items: flex-start; gap: 10px; font-size: 12px; }
.format-dot { width: 8px; height: 8px; border-radius: 50%; margin-top: 5px; flex-shrink: 0; }

.status-legend { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
</style>
