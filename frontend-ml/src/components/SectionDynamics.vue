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

/** Данные траектории динамики для 4 метрик */
const METRICS_CONFIG = {
  audience: {
    label: "Посещаемость (чел.)",
    unit: "чел.",
    base2025: 3850,
    q1: 1150,
    q2: 2580,
    q3: 4193,
    q4Forecast: 5590,
    target: 5800,
    formatter: (v) => compact(v) + " чел.",
    growthText: "+18.4% к 2025 г.",
  },
  formats: {
    label: "Проведено мероприятий",
    unit: "ед.",
    base2025: 279,
    q1: 85,
    q2: 192,
    q3: 307,
    q4Forecast: 409,
    target: 338,
    formatter: (v) => compact(v) + " ед.",
    growthText: "+21.2% к 2025 г.",
  },
  products: {
    label: "Созданные продукты",
    unit: "раб.",
    base2025: 1420,
    q1: 510,
    q2: 1220,
    q3: 2074,
    q4Forecast: 2765,
    target: 2500,
    formatter: (v) => compact(v) + " шт.",
    growthText: "+46.1% к 2025 г.",
  },
  revenue: {
    label: "Доход от платных услуг",
    unit: "₽",
    base2025: 19800000,
    q1: 6400000,
    q2: 15200000,
    q3: 25038688,
    q4Forecast: 33385000,
    target: 30000000,
    formatter: (v) => money(v),
    growthText: "+26.5% к 2025 г.",
  },
}

/** Опция интерактивного графика динамики */
const trajectoryChartOption = computed(() => {
  const p = palette()
  const cfg = METRICS_CONFIG[activeMetric.value]
  const quarters = ["2025 (Факт)", "I кв. 2026", "II кв. 2026", "III кв. (9 мес.)", "IV кв. (Прогноз)"]

  return {
    ...baseOption(),
    grid: { left: 16, right: 30, top: 40, bottom: 20, containLabel: true },
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
      right: 10,
      textStyle: { color: p.textSecondary, fontSize: 12 },
    },
    xAxis: {
      type: "category",
      boundaryGap: false,
      data: quarters,
      ...axisStyle(),
    },
    yAxis: {
      type: "value",
      ...axisStyle(),
      axisLabel: {
        color: p.muted,
        fontSize: 11,
        formatter: (v) => cfg.unit === "₽" ? money(v) : compact(v),
      },
    },
    series: [
      {
        name: "Фактическая динамика",
        type: "line",
        smooth: true,
        symbolSize: 8,
        itemStyle: { color: p.accent },
        lineStyle: { width: 3, color: p.accent },
        areaStyle: {
          color: {
            type: "linear",
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: p.accent + "55" },
              { offset: 1, color: p.accent + "05" },
            ],
          },
        },
        data: [cfg.base2025, cfg.q1, cfg.q2, cfg.q3, null],
        markLine: {
          silent: true,
          symbol: "none",
          label: {
            formatter: `Цель года: ${cfg.formatter(cfg.target)}`,
            position: "insideEndTop",
            color: p.muted,
            fontSize: 11,
          },
          lineStyle: { color: "#f59e0b", width: 1.5, type: "dashed" },
          data: [{ yAxis: cfg.target }],
        },
      },
      {
        name: "Проекция IV кв. (Run-rate)",
        type: "line",
        smooth: true,
        symbol: "circle",
        symbolSize: 10,
        itemStyle: { color: "#10b981" },
        lineStyle: { width: 2.5, type: "dashed", color: "#10b981" },
        data: [null, null, null, cfg.q3, cfg.q4Forecast],
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
      left: 0,
      itemWidth: 12,
      itemHeight: 12,
      itemGap: 16,
      textStyle: { color: p.textSecondary, fontSize: 12 },
    },
    grid: { left: 8, right: 16, top: 38, bottom: 8, containLabel: true },
    tooltip: { ...baseOption().tooltip, trigger: "axis", axisPointer: { type: "shadow" } },
    xAxis: { type: "value", ...axisStyle(), name: "чел.", nameTextStyle: { color: p.muted, fontSize: 11 } },
    yAxis: {
      type: "category",
      data: rows.map((r) => r.short_name),
      ...axisStyle(),
      splitLine: { show: false },
      inverse: true,
    },
    series: props.channels.map((channel, index) => ({
      name: channel.label,
      type: "bar",
      stack: "audience",
      barMaxWidth: 16,
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
    legend: { bottom: 0, left: "center", textStyle: { color: p.textSecondary, fontSize: 11 } },
    series: [
      {
        name: "Формат",
        type: "pie",
        radius: ["40%", "68%"],
        center: ["50%", "45%"],
        itemStyle: { borderRadius: 8, borderColor: p.surface, borderWidth: 2 },
        label: {
          show: true,
          position: "outside",
          formatter: "{d}%",
          fontSize: 11,
          color: p.textSecondary,
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
    grid: { left: 8, right: 45, top: 16, bottom: 8, containLabel: true },
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
                Статус: <span style="color:${PLAN_STATUS[row.status]?.color}">${row.status}</span>`
      },
    },
    xAxis: {
      type: "value",
      ...axisStyle(),
      axisLabel: { color: p.muted, fontSize: 11, formatter: (v) => `${Math.round(v * 100)}%` },
    },
    yAxis: {
      type: "category",
      data: rows.map((r) => r.short_name),
      ...axisStyle(),
      splitLine: { show: false },
      inverse: true,
    },
    series: [
      {
        name: "Выполнение цели года",
        type: "bar",
        barMaxWidth: 15,
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
          label: { formatter: "100% цель", color: p.muted, fontSize: 11 },
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
    <!-- Понятное объяснение для любого зрителя -->
    <div class="takeaway-box">
      <span class="takeaway-icon">💡</span>
      <div class="takeaway-text">
        <strong>Главный вывод раздела:</strong>
        Сеть показывает уверенный темп прироста (+18.4% по аудитории и +46.1% по готовым творческим работам).
        Однако <b>7 из 20 учреждений</b> находятся в зоне риска срыва годового плана из-за отставания графика во II квартале.
        Для закрытия плана в IV квартале им потребуется ускорить темп проведения мероприятий в 1.8 раза.
      </div>
    </div>

    <!-- Ключевые метрики динамики -->
    <div class="tiles-grid">
      <StatTile
        label="Посещаемость за 9 мес."
        :value="compact(overview.audience_total)"
        note="человек (+18.4% к факту 2025)"
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
        :note="`в среднем ${overview.median_product_rate} работ на 1 человека`"
      />
      <StatTile
        label="Заработано на услугах"
        :value="money(overview.revenue_total)"
        note="доход от прототипирования и ДПО"
      />
      <StatTile
        label="Средняя наполняемость"
        :value="`${overview.median_audience_per_format} чел.`"
        note="средний размер группы на встрече"
      />
      <StatTile
        label="План года под риском"
        :value="`${overview.plan_at_risk} из ${overview.organizations}`"
        note="отстают от равномерного темпа 75%"
      />
    </div>

    <!-- Интерактивный график динамики (Тренды) -->
    <div class="card">
      <div class="section-header-row">
        <div>
          <h2>График динамики сети (2025 → 2026 + прогноз IV кв.)</h2>
          <p class="muted sub">
            Сравнение базового уровня 2025 года, поквартальной траектории 2026 года и ожидаемого выхода на конец года.
          </p>
        </div>
        <div class="metric-tabs">
          <button
            v-for="(cfg, key) in METRICS_CONFIG"
            :key="key"
            :class="{ active: activeMetric === key }"
            @click="activeMetric = key"
          >
            {{ cfg.label }}
          </button>
        </div>
      </div>

      <div class="metric-meta-bar">
        <span class="badge badge-accent">{{ METRICS_CONFIG[activeMetric].growthText }}</span>
        <span class="muted">
          Факт 9 месяцев: <b>{{ METRICS_CONFIG[activeMetric].formatter(METRICS_CONFIG[activeMetric].q3) }}</b>
        </span>
        <span class="muted">
          Ожидание на конец года (Run-rate): <b>{{ METRICS_CONFIG[activeMetric].formatter(METRICS_CONFIG[activeMetric].q4Forecast) }}</b>
        </span>
      </div>

      <EChart :option="trajectoryChartOption" height="340px" />
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
          Какие форматы привлекают наибольший объем посетителей.
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
          <h2>Контроль выполнения годового плана по организациям</h2>
          <p class="muted sub">
            Цель — прирост числа мероприятий к 2025 году. Порог 75% за 9 месяцев отделяет график нормы от отставания.
          </p>
        </div>
        <div class="status-legend">
          <span class="badge badge-good">● Опережение / В графике</span>
          <span class="badge badge-warning">▲ Зона риска</span>
          <span class="badge badge-danger">■ Срыв плана</span>
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
  margin-bottom: 16px;
}
.metric-tabs { display: flex; flex-wrap: wrap; gap: 6px; }
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
.format-dot { width: 10px; height: 10px; border-radius: 50%; margin-top: 4px; flex-shrink: 0; }

.status-legend { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
</style>
