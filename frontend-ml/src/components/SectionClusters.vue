<script setup>
/** Кластеры аудиторных моделей: пространство признаков, портреты, проверки. */
import { computed } from 'vue'
import EChart from './EChart.vue'
import { axisStyle, baseOption, palette } from '../theme'

const props = defineProps({
  clusters: { type: Object, required: true },
  validation: { type: Object, required: true },
})

const variance = computed(() => {
  const shown = props.clusters.explained_variance.slice(0, props.clusters.components)
  return Math.round(shown.reduce((a, b) => a + b, 0) * 100)
})

/**
 * Малые кратные вместо пяти цветов на одной диаграмме рассеяния.
 *
 * Пять категориальных цветов не проходят проверку различимости по всем парам,
 * а на точечной диаграмме в сравнении участвуют именно все пары. Поэтому для
 * каждого кластера рисуется отдельная панель: выделенный кластер — акцентным
 * цветом, остальная сеть — приглушённым серым как контекст.
 */
function panelOption(clusterId) {
  const p = palette()
  const points = props.clusters.embedding
  const inside = points.filter((d) => d.cluster === clusterId)
  const outside = points.filter((d) => d.cluster !== clusterId)

  return {
    ...baseOption(),
    grid: { left: 4, right: 12, top: 12, bottom: 4, containLabel: true },
    tooltip: {
      ...baseOption().tooltip,
      formatter: (item) => {
        const d = item.data
        return `<b>${d[3]}</b><br/>аудитория: ${d[2]} чел.<br/>силуэт: ${d[4]}`
      },
    },
    xAxis: { type: 'value', ...axisStyle(), axisLabel: { show: false }, name: '' },
    yAxis: { type: 'value', ...axisStyle(), axisLabel: { show: false } },
    series: [
      {
        name: 'остальная сеть',
        type: 'scatter',
        symbolSize: 9,
        itemStyle: { color: p.dim, borderColor: p.surface, borderWidth: 2 },
        data: outside.map((d) => [d.pc1, d.pc2, d.audience_total, d.name, d.silhouette]),
      },
      {
        name: 'кластер',
        type: 'scatter',
        symbolSize: 13,
        itemStyle: { color: p.accent, borderColor: p.surface, borderWidth: 2 },
        data: inside.map((d) => [d.pc1, d.pc2, d.audience_total, d.name, d.silhouette]),
      },
    ],
  }
}

const profiles = computed(() => props.clusters.profiles)
const clustering = computed(() => props.validation.clustering)
const recStability = computed(() => props.validation.recommendations)
</script>

<template>
  <div class="stack">
    <div class="card">
      <h2>Проверка разбиения</h2>
      <p class="muted sub">
        Кластеризация вернёт группы на любых данных, включая шум. Ниже — три независимые
        проверки того, что найденная структура относится к данным, а не к алгоритму.
      </p>
      <div class="checks">
        <div class="check">
          <div class="check-label">Значимость структуры</div>
          <div class="check-value">p = {{ clustering.permutation_p_value }}</div>
          <div class="check-note">
            силуэт {{ clustering.observed_silhouette }} против {{ clustering.permutation_mean }}
            у случайных разбиений — выше на {{ clustering.effect_size }}&nbsp;σ
          </div>
        </div>
        <div class="check">
          <div class="check-label">Воспроизводимость состава</div>
          <div class="check-value">ARI = {{ clustering.loo_mean_ari }}</div>
          <div class="check-note">
            среднее по 20 прогонам с исключением одного центра, минимум {{ clustering.loo_min_ari }}
          </div>
        </div>
        <div class="check">
          <div class="check-label">Устойчивость рекомендаций</div>
          <div class="check-value">{{ Math.round(recStability.stable_share * 100) }} %</div>
          <div class="check-note">
            выводов сохраняются при исключении любого одного центра из эталонной группы
          </div>
        </div>
        <div class="check">
          <div class="check-label">Согласие алгоритмов</div>
          <div class="check-value">
            {{ clusters.agreement['kmeans~ward'] }}
          </div>
          <div class="check-note">ARI между k-средними и методом Уорда на одном пространстве</div>
        </div>
      </div>
      <p class="verdict">{{ clustering.verdict }}</p>
    </div>

    <div class="card">
      <h2>Пространство аудиторных моделей</h2>
      <p class="muted sub">
        Панели показывают одно и то же пространство главных компонент
        ({{ clusters.components }} компоненты, {{ variance }} % дисперсии). В каждой панели
        выделен свой кластер, остальная сеть дана серым как контекст — так пять групп
        различаются положением, а не оттенком.
      </p>
      <div class="panels">
        <figure v-for="profile in profiles" :key="profile.cluster_id">
          <figcaption>
            <b>{{ profile.name }}</b>
            <span class="muted"> · {{ profile.size }}</span>
          </figcaption>
          <EChart :option="panelOption(profile.cluster_id)" height="170px" />
        </figure>
      </div>
    </div>

    <div class="cards">
      <article v-for="profile in profiles" :key="profile.cluster_id" class="card">
        <h3>{{ profile.name }}</h3>
        <p class="muted summary">{{ profile.summary }}</p>
        <dl>
          <div v-for="d in profile.distinctive" :key="d.feature">
            <dt>{{ d.description }}</dt>
            <dd :class="d.z >= 0 ? 'up' : 'down'">{{ d.z > 0 ? '+' : '' }}{{ d.z }} σ</dd>
          </div>
        </dl>
        <ul class="members">
          <li v-for="(name, i) in profile.member_names" :key="name">
            {{ name }}
            <span class="muted conf">{{ validation.clustering.membership_confidence[profile.members[i]] }}</span>
          </li>
        </ul>
        <p class="muted foot">средний силуэт {{ profile.mean_silhouette }}</p>
      </article>
    </div>
  </div>
</template>

<style scoped>
.stack { display: flex; flex-direction: column; gap: 20px; }
.sub { font-size: 13px; margin-top: 6px; max-width: 80ch; }
.checks {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-top: 18px;
}
.check-label { font-size: 12px; color: var(--muted); }
.check-value { font-size: 22px; font-weight: 600; margin: 4px 0; }
.check-note { font-size: 12px; color: var(--text-secondary); }
.verdict {
  margin-top: 18px;
  padding: 10px 14px;
  border-left: 2px solid var(--accent);
  background: var(--accent-wash);
  border-radius: 0 8px 8px 0;
  font-size: 13px;
}
.panels { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 18px; margin-top: 14px; }
figure { margin: 0; }
figcaption { font-size: 13px; margin-bottom: 4px; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }
.summary { font-size: 12px; margin: 6px 0 14px; }
dl { margin: 0 0 14px; display: flex; flex-direction: column; gap: 6px; }
dl > div { display: flex; justify-content: space-between; gap: 12px; font-size: 12px; }
dt { color: var(--text-secondary); }
dd { margin: 0; font-variant-numeric: tabular-nums; white-space: nowrap; }
dd.up { color: var(--text-primary); }
dd.down { color: var(--muted); }
.members { list-style: none; margin: 0; padding: 12px 0 0; border-top: 1px solid var(--border); font-size: 13px; }
.members li { display: flex; justify-content: space-between; padding: 3px 0; }
.conf { font-variant-numeric: tabular-nums; font-size: 12px; }
.foot { font-size: 12px; margin-top: 10px; }
</style>
