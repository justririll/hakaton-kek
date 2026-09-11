<script setup>
/** Обёртка над ECharts: следит за размером контейнера и сменой темы. */
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
// Точечный импорт вместо всего пакета: в дашборде используются только
// столбиковые и точечные диаграммы, полный набор тянет лишний мегабайт.
import * as echarts from 'echarts/core'
import { BarChart, ScatterChart, LineChart, RadarChart, PieChart } from 'echarts/charts'
import {
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  MarkPointComponent,
  TooltipComponent,
  RadarComponent,
  TitleComponent,
  GraphicComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([
  BarChart,
  ScatterChart,
  LineChart,
  RadarChart,
  PieChart,
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  MarkPointComponent,
  TooltipComponent,
  RadarComponent,
  TitleComponent,
  GraphicComponent,
  CanvasRenderer,
])

const props = defineProps({
  option: { type: Object, required: true },
  height: { type: String, default: '280px' },
})

const host = ref(null)
let chart = null
let observer = null
let media = null

function render() {
  if (!chart) return
  // notMerge: опция пересобирается целиком, иначе остатки прошлой серии
  // всплывают при смене набора данных.
  chart.setOption(props.option, true)
}

onMounted(() => {
  chart = echarts.init(host.value, null, { renderer: 'canvas' })
  render()

  observer = new ResizeObserver(() => chart && chart.resize())
  observer.observe(host.value)

  media = window.matchMedia('(prefers-color-scheme: dark)')
  media.addEventListener('change', render)
})

onBeforeUnmount(() => {
  observer?.disconnect()
  media?.removeEventListener('change', render)
  chart?.dispose()
})

watch(() => props.option, render, { deep: true })
</script>

<template>
  <div ref="host" :style="{ height, width: '100%' }" />
</template>
