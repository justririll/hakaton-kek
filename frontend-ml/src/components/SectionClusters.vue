<script setup>
/**
 * Раздел «Кластеризация аудитории»:
 * 5 аудиторных моделей (архетипов), радарный профиль,
 * 2D-карта сходства центров и сравнительная матрица.
 */
import { computed, ref } from "vue"
import Disclosure from "./Disclosure.vue"
import EChart from "./EChart.vue"
import { axisStyle, baseOption, compact, palette, getClusterMeta, CLUSTER_METAS } from "../theme"

const props = defineProps({
  clusters: { type: Object, required: true },
  validation: { type: Object, required: true },
  organizations: { type: Array, required: true },
})

const emit = defineEmits(["select-org"])

// Выбранный архетип (0-4)
const selectedClusterId = ref(0)

const byId = computed(() => {
  const map = {}
  for (const org of props.organizations) map[org.org_id] = org
  return map
})

const selectedProfile = computed(() => {
  return props.clusters.profiles.find((p) => p.cluster_id === selectedClusterId.value) || props.clusters.profiles[0]
})

const selectedMeta = computed(() => getClusterMeta(selectedClusterId.value))

/** Члены выбранного кластера */
const selectedMembers = computed(() => {
  if (!selectedProfile.value) return []
  return selectedProfile.value.members.map((id) => byId.value[id]).filter(Boolean)
})

/** Лепестковая диаграмма (Radar Chart) выбранного кластера vs Сеть */
const radarOption = computed(() => {
  const p = palette()
  const meta = selectedMeta.value
  const members = selectedMembers.value
  const count = members.length || 1

  // Расчет нормализованных баллов 0-100 для кластера
  const avgAudience = members.reduce((acc, m) => acc + (m.audience_total || 0), 0) / count
  const avgProducts = members.reduce((acc, m) => acc + (m.products_total || 0), 0) / count
  const avgResidents = members.reduce((acc, m) => acc + (m.residents_total || 0), 0) / count
  const avgRevenue = members.reduce((acc, m) => acc + (m.revenue_total || 0), 0) / count
  const avgPubs = members.reduce((acc, m) => acc + (m.media_publications || 0), 0) / count

  const scoreAudience = Math.min(100, Math.max(15, Math.round((avgAudience / 500) * 100)))
  const scoreProducts = Math.min(100, Math.max(15, Math.round((avgProducts / 250) * 100)))
  const scoreResidents = Math.min(100, Math.max(15, Math.round((avgResidents / 400) * 100)))
  const scoreRevenue = Math.min(100, Math.max(15, Math.round((avgRevenue / 2500000) * 100)))
  const scorePubs = Math.min(100, Math.max(15, Math.round((avgPubs / 80) * 100)))

  return {
    ...baseOption(),
    tooltip: { trigger: "item" },
    legend: {
      bottom: 0,
      textStyle: { color: p.textSecondary, fontSize: 11 },
    },
    radar: {
      indicator: [
        { name: "Охват аудитории", max: 100 },
        { name: "Выход арт-продуктов", max: 100 },
        { name: "Лояльность (резиденты)", max: 100 },
        { name: "Монетизация услуг", max: 100 },
        { name: "Медийный резонанс", max: 100 },
      ],
      shape: "circle",
      radius: "50%",
      center: ["50%", "44%"],
      splitNumber: 4,
      axisName: { color: p.textSecondary, fontSize: 10 },
      splitLine: { lineStyle: { color: p.grid } },
      splitArea: { show: false },
      axisLine: { lineStyle: { color: p.border } },
    },
    series: [
      {
        name: "Сравнение профилей",
        type: "radar",
        data: [
          {
            value: [scoreAudience, scoreProducts, scoreResidents, scoreRevenue, scorePubs],
            name: `${meta.name}`,
            symbolSize: 6,
            itemStyle: { color: meta.color },
            areaStyle: { color: meta.color + "25" },
            lineStyle: { width: 2, color: meta.color },
          },
          {
            value: [50, 50, 50, 50, 50],
            name: "Средняя норма сети",
            symbolSize: 4,
            itemStyle: { color: p.muted },
            lineStyle: { width: 1.5, type: "dashed", color: p.muted },
          },
        ],
      },
    ],
  }
})

/** Интерактивная 2D карта сходства центров (Scatter Plot) */
const scatterMapOption = computed(() => {
  const p = palette()
  const points = props.clusters.embedding

  const series = props.clusters.profiles.map((profile) => {
    const meta = getClusterMeta(profile.cluster_id)
    const clusterPoints = points.filter((d) => d.cluster === profile.cluster_id)
    const isSelected = profile.cluster_id === selectedClusterId.value

    return {
      name: meta.name,
      type: "scatter",
      symbolSize: isSelected ? 16 : 10,
      itemStyle: {
        color: meta.color,
        borderColor: p.surface,
        borderWidth: 2,
        opacity: isSelected ? 1.0 : 0.4,
      },
      data: clusterPoints.map((d) => [d.pc1, d.pc2, d.audience_total, d.name, d.org_id]),
    }
  })

  return {
    ...baseOption(),
    grid: { left: 20, right: 20, top: 20, bottom: 20, containLabel: true },
    tooltip: {
      ...baseOption().tooltip,
      formatter: (item) => {
        const d = item.data
        return `<b>${d[3]}</b><br/>
                Аудитория: <b>${compact(d[2])} чел.</b><br/>
                Архетип: <b>${item.seriesName}</b><br/>
                <i>Кликните для перехода к досье</i>`
      },
    },
    xAxis: { type: "value", ...axisStyle(), axisLabel: { show: false }, splitLine: { lineStyle: { color: p.grid } } },
    yAxis: { type: "value", ...axisStyle(), axisLabel: { show: false }, splitLine: { lineStyle: { color: p.grid } } },
    series,
  }
})
</script>

<template>
  <div class="stack">
    <!-- Понятное объяснение -->
    <div class="takeaway-box">
      <div class="takeaway-text">
        <strong>Зачем нужна кластеризация аудитории:</strong>
        Нельзя оценивать профильное хореографическое училище на 20 человек и многотысячный институт культуры одной линейкой.
        Машинное обучение разделило 20 центров на <b>5 архетипов</b> на основе состава аудитории, формата обучения и глубины работы.
        Каждый центр сравнивается исключительно со своими коллегами по модели — разрыв между ними и лучшими и есть реальный резерв роста.
      </div>
    </div>

    <!-- 5 карточек архетипов -->
    <div class="archetypes-grid">
      <article
        v-for="profile in clusters.profiles"
        :key="profile.cluster_id"
        class="archetype-card"
        :class="{ active: selectedClusterId === profile.cluster_id }"
        :style="{
          '--cluster-color': getClusterMeta(profile.cluster_id).color,
          '--cluster-glow': getClusterMeta(profile.cluster_id).glow,
        }"
        @click="selectedClusterId = profile.cluster_id"
      >
        <div class="arch-top">
          <span class="arch-code-badge">{{ getClusterMeta(profile.cluster_id).code }}</span>
          <span class="arch-count">{{ profile.size }} центров</span>
        </div>
        <h3 class="arch-title">{{ profile.name }}</h3>
        <span class="arch-badge">{{ getClusterMeta(profile.cluster_id).badge }}</span>
        <p class="arch-desc">{{ profile.summary }}</p>
      </article>
    </div>

    <!-- Две колонки: Профиль выбранного кластера (Радар) и Состав участников -->
    <div class="two-col-grid">
      <div class="card">
        <div class="profile-header">
          <div>
            <div class="badge badge-accent">
              Архетип: {{ selectedMeta.name }}
            </div>
            <h2>Радарный профиль модели на фоне сети</h2>
            <p class="muted sub">
              Сопоставление сильных и слабых сторон архетипа по 5 ключевым осям деятельности.
            </p>
          </div>
        </div>
        <EChart :option="radarOption" height="320px" />
      </div>

      <div class="card">
        <h2>Центры в архетипе «{{ selectedMeta.name }}»</h2>
        <p class="muted sub">
          {{ selectedProfile.size }} организаций со схожей аудиторной структурой:
        </p>

        <div class="members-list">
          <div
            v-for="m in selectedMembers"
            :key="m.org_id"
            class="member-card"
            @click="emit('select-org', m.org_id)"
          >
            <div class="member-info">
              <strong>{{ m.short_name }}</strong>
              <small class="muted">{{ m.full_name?.slice(0, 50) }}...</small>
            </div>
            <div class="member-stats">
              <span class="stat-pill">{{ compact(m.audience_total) }} чел.</span>
              <span class="stat-pill">{{ compact(m.products_total) }} арт-работ</span>
            </div>
          </div>
        </div>

        <div class="distinctive-box">
          <div class="distinctive-title">
            <strong>Отличительные черты архетипа:</strong>
            <span v-if="selectedProfile.summary" class="distinctive-sub">{{ selectedProfile.summary }}</span>
          </div>

          <div v-if="Array.isArray(selectedProfile.distinctive) && selectedProfile.distinctive.length" class="traits-grid">
            <div
              v-for="(trait, ti) in selectedProfile.distinctive"
              :key="ti"
              class="trait-card"
            >
              <div class="trait-main">
                <span class="trait-bullet">•</span>
                <span class="trait-name">{{ trait.label || trait.description }}</span>
                <span v-if="trait.label && trait.description" class="trait-desc muted">({{ trait.description }})</span>
              </div>
              <span
                v-if="trait.z !== undefined"
                class="trait-badge mono-nums"
                :class="trait.z > 0 ? 'badge-good' : 'badge-neutral'"
              >
                {{ trait.z > 0 ? '+' : '' }}{{ typeof trait.z === 'number' ? trait.z.toFixed(2) : trait.z }}σ
              </span>
            </div>
          </div>
          <p v-else class="muted">{{ selectedProfile.summary || 'Нет специфических отклонений' }}</p>
        </div>
      </div>
    </div>

    <!-- Интерактивная 2D карта схожести центров -->
    <div class="card">
      <div class="section-header-row">
        <div>
          <h2>Карта сети (Проекция сходства моделей)</h2>
          <p class="muted sub">
            Близость точек на карте означает сходство структуры аудитории и форматов. Выделенный архетип подсвечен.
          </p>
        </div>
        <div class="cluster-pills">
          <button
            v-for="p in clusters.profiles"
            :key="p.cluster_id"
            class="cluster-pill-btn"
            :class="{ active: selectedClusterId === p.cluster_id }"
            :style="{ borderColor: getClusterMeta(p.cluster_id).color }"
            @click="selectedClusterId = p.cluster_id"
          >
            {{ getClusterMeta(p.cluster_id).shortName }}
          </button>
        </div>
      </div>
      <EChart :option="scatterMapOption" height="340px" />
    </div>

    <!-- Статистическая верификация для экспертов -->
    <section class="card">
      <h2>Математическая верификация кластеризации</h2>
      <p class="muted sub">
        Параметры доказательности алгоритмов для экспертного аудита:
      </p>
      <Disclosure label="Показать параметры валидации и устойчивости">
        <div class="validation-details">
          <p>
            <b>Обоснованность разбиения:</b> Перестановочный тест (2 000 итераций) подтверждает неслучайность структуры:
            p-value = <b>{{ validation.clustering.permutation_p_value }}</b> при среднем силуэте <b>{{ validation.clustering.observed_silhouette }}</b>.
          </p>
          <p>
            <b>Устойчивость к исключению объектов (Leave-One-Out):</b> Средний индекс ARI при поочередном удалении центров равен
            <b>{{ validation.clustering.loo_mean_ari }}</b> (минимальный {{ validation.clustering.loo_min_ari }}).
          </p>
          <p>
            <b>Согласие независимых методов:</b> K-Means и иерархический метод Уорда дали идентичную структуру
            (ARI = <b>{{ clusters.agreement['kmeans~ward'] }}</b>).
          </p>
        </div>
      </Disclosure>
    </section>
  </div>
</template>

<style scoped>
.stack { display: flex; flex-direction: column; gap: 24px; }
.sub { font-size: 13px; margin-top: 2px; }

.archetypes-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
  gap: 14px;
}
.archetype-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.archetype-card:hover {
  transform: translateY(-2px);
  border-color: var(--cluster-color);
  box-shadow: 0 4px 14px var(--cluster-glow);
}
.archetype-card.active {
  border-color: var(--cluster-color);
  box-shadow: 0 0 0 2px var(--cluster-color), 0 6px 18px var(--cluster-glow);
}
.arch-top { display: flex; justify-content: space-between; align-items: center; }
.arch-code-badge {
  font-size: 11px;
  font-weight: 700;
  font-family: monospace;
  color: var(--cluster-color);
  background: var(--raised);
  padding: 2px 6px;
  border-radius: 4px;
}
.arch-count { font-size: 11px; font-weight: 600; color: var(--muted); text-transform: uppercase; }
.arch-title { font-size: 15px; font-weight: 700; margin: 0; }
.arch-badge {
  font-size: 11px;
  font-weight: 600;
  color: var(--cluster-color);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.arch-desc { font-size: 12px; line-height: 1.45; color: var(--text-secondary); margin: 0; }

.two-col-grid {
  display: grid;
  grid-template-columns: 1.1fr 1fr;
  gap: 20px;
}
@media (max-width: 860px) {
  .two-col-grid { grid-template-columns: 1fr; }
}

.profile-header { margin-bottom: 12px; }
.members-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 12px;
  max-height: 240px;
  overflow-y: auto;
}
.member-card {
  background: var(--raised);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  transition: all 0.15s ease;
}
.member-card:hover {
  background: var(--accent-wash);
  border-color: var(--accent);
}
.member-info { display: flex; flex-direction: column; gap: 2px; }
.member-stats { display: flex; flex-direction: column; gap: 4px; align-items: flex-end; }
.stat-pill { font-size: 11px; font-weight: 600; background: var(--surface); padding: 2px 6px; border-radius: 4px; }

.distinctive-box {
  margin-top: 14px;
  padding: 12px 14px;
  background: var(--raised);
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.distinctive-title {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.distinctive-sub {
  color: var(--text-secondary);
  font-size: 12px;
}
.traits-grid {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.trait-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--surface);
  padding: 6px 10px;
  border-radius: 6px;
  border: 1px solid var(--border);
  gap: 8px;
}
.trait-main {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.trait-bullet {
  color: var(--accent);
  font-weight: bold;
}
.trait-name {
  font-weight: 500;
}
.trait-desc {
  font-size: 11px;
}
.trait-badge {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 4px;
  white-space: nowrap;
}

.section-header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 14px;
}
.cluster-pills { display: flex; flex-wrap: wrap; gap: 4px; }
.cluster-pill-btn {
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 6px;
}

.validation-details { font-size: 13px; line-height: 1.6; display: flex; flex-direction: column; gap: 8px; }
</style>
