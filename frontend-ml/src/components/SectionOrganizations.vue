<script setup>
/**
 * Каталог центров культуры сети (20 организаций):
 * Поиск, фильтры по архетипам и выполнению плана,
 * сравнительные карточки и переход в детальное досье.
 */
import { computed, ref } from "vue"
import { compact, money, percent, PLAN_STATUS, getClusterMeta } from "../theme"

const props = defineProps({
  organizations: { type: Array, required: true },
  plan: { type: Array, required: true },
  clusters: { type: Object, required: true },
})

const emit = defineEmits(["select-org"])

const search = ref("")
const selectedCluster = ref("all")
const selectedStatus = ref("all")
const sortBy = ref("audience")

const enrichedOrgs = computed(() => {
  const planMap = {}
  for (const p of props.plan) planMap[p.org_id] = p

  return props.organizations.map((org) => ({
    ...org,
    planInfo: planMap[org.org_id] || {},
    clusterMeta: getClusterMeta(org.cluster),
  }))
})

const filteredOrgs = computed(() => {
  const q = search.value.toLowerCase().trim()
  return enrichedOrgs.value
    .filter((org) => {
      const matchSearch =
        !q ||
        org.short_name.toLowerCase().includes(q) ||
        (org.full_name && org.full_name.toLowerCase().includes(q))
      const matchCluster =
        selectedCluster.value === "all" || org.cluster === Number(selectedCluster.value)
      const matchStatus =
        selectedStatus.value === "all" || org.planInfo.status === selectedStatus.value
      return matchSearch && matchCluster && matchStatus
    })
    .sort((a, b) => {
      if (sortBy.value === "audience") return b.audience_total - a.audience_total
      if (sortBy.value === "plan") return (b.planInfo.completion || 0) - (a.planInfo.completion || 0)
      if (sortBy.value === "products") return b.products_total - a.products_total
      if (sortBy.value === "revenue") return b.revenue_total - a.revenue_total
      return 0
    })
})
</script>

<template>
  <div class="stack">
    <!-- Резюме -->
    <div class="takeaway-box">
      <div class="takeaway-text">
        <strong>Каталог учреждений сети:</strong>
        Все <b>20 центров прототипирования</b> творческих вузов РФ.
        Выберите организацию для перехода в досье с анализом форматов обучения,
        статусом годового плана и персональными рекомендациями.
      </div>
    </div>

    <!-- Панель поиска и фильтров -->
    <div class="card filter-panel">
      <div class="top-row">
        <div class="search-box">
          <input
            type="search"
            v-model="search"
            placeholder="Поиск по названию организации..."
          />
        </div>
        <div class="sort-box">
          <span class="muted">Сортировка:</span>
          <select v-model="sortBy">
            <option value="audience">Посещаемость (чел.)</option>
            <option value="plan">Выполнение плана (%)</option>
            <option value="products">Арт-продукты (шт.)</option>
            <option value="revenue">Доход от услуг (₽)</option>
          </select>
        </div>
      </div>

      <div class="filters-row">
        <div class="filter-cluster-group">
          <span class="filter-label muted">Архетип:</span>
          <button
            class="pill-btn"
            :class="{ active: selectedCluster === 'all' }"
            @click="selectedCluster = 'all'"
          >
            Все (20)
          </button>
          <button
            v-for="p in clusters.profiles"
            :key="p.cluster_id"
            class="pill-btn"
            :class="{ active: selectedCluster === String(p.cluster_id) }"
            @click="selectedCluster = String(p.cluster_id)"
          >
            {{ getClusterMeta(p.cluster_id).shortName }}
          </button>
        </div>

        <div class="filter-status-group">
          <span class="filter-label muted">План:</span>
          <button
            class="pill-btn"
            :class="{ active: selectedStatus === 'all' }"
            @click="selectedStatus = 'all'"
          >
            Все
          </button>
          <button
            class="pill-btn"
            :class="{ active: selectedStatus === 'опережение' }"
            @click="selectedStatus = 'опережение'"
          >
            Опережение
          </button>
          <button
            class="pill-btn"
            :class="{ active: selectedStatus === 'в графике' }"
            @click="selectedStatus = 'в графике'"
          >
            В графике
          </button>
          <button
            class="pill-btn"
            :class="{ active: selectedStatus === 'риск' }"
            @click="selectedStatus = 'риск'"
          >
            Риск
          </button>
          <button
            class="pill-btn"
            :class="{ active: selectedStatus === 'срыв' }"
            @click="selectedStatus = 'срыв'"
          >
            Срыв
          </button>
        </div>
      </div>
    </div>

    <!-- Сетка карточек учреждений -->
    <div class="orgs-grid">
      <article
        v-for="org in filteredOrgs"
        :key="org.org_id"
        class="card org-card"
        @click="emit('select-org', org.org_id)"
      >
        <div class="card-header">
          <div class="card-tags">
            <span
              class="badge badge-neutral cluster-tag"
              :style="{ color: org.clusterMeta.color }"
              :title="org.clusterMeta.name"
            >
              {{ org.clusterMeta.shortName || org.clusterMeta.name }}
            </span>
            <span
              v-if="org.planInfo.status"
              class="badge status-tag"
              :class="{
                'badge-good': org.planInfo.status === 'опережение' || org.planInfo.status === 'в графике',
                'badge-warning': org.planInfo.status === 'риск',
                'badge-danger': org.planInfo.status === 'срыв',
                'badge-neutral': org.planInfo.status === 'без базы',
              }"
            >
              {{ org.planInfo.status }}
            </span>
          </div>
          <h3 class="org-title">{{ org.short_name }}</h3>
        </div>

        <p class="org-full muted">{{ org.full_name?.slice(0, 75) }}...</p>

        <!-- Прогресс плана -->
        <div v-if="org.planInfo.completion !== undefined" class="plan-mini">
          <div class="plan-mini-labels">
            <span class="muted">Выполнение плана:</span>
            <strong class="mono-nums">{{ percent(org.planInfo.completion) }}</strong>
          </div>
          <div class="track">
            <div
              class="fill"
              :style="{
                width: `${Math.min(100, Math.round(org.planInfo.completion * 100))}%`,
                backgroundColor: PLAN_STATUS[org.planInfo.status]?.color || 'var(--accent)',
              }"
            />
          </div>
        </div>

        <!-- 4 Ключевые метрики -->
        <div class="metrics-grid">
          <div class="m-cell">
            <span class="m-key">Посещаемость</span>
            <strong class="m-val">{{ compact(org.audience_total) }}</strong>
          </div>
          <div class="m-cell">
            <span class="m-key">Форматов</span>
            <strong class="m-val">{{ compact(org.supply_total) }}</strong>
          </div>
          <div class="m-cell">
            <span class="m-key">Арт-продуктов</span>
            <strong class="m-val">{{ compact(org.products_total) }}</strong>
          </div>
          <div class="m-cell">
            <span class="m-key">Выручка</span>
            <strong class="m-val">{{ money(org.revenue_total) }}</strong>
          </div>
        </div>

        <div class="card-footer">
          <span class="view-hint">Открыть досье →</span>
        </div>
      </article>

      <div v-if="!filteredOrgs.length" class="empty-state card">
        <p class="muted">Организаций по заданным критериям не найдено.</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.stack { display: flex; flex-direction: column; gap: 24px; }

.filter-panel { display: flex; flex-direction: column; gap: 14px; }
.top-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}
.search-box { flex: 1; min-width: 260px; }
.search-box input { width: 100%; }
.sort-box { display: flex; align-items: center; gap: 8px; font-size: 13px; }

.filters-row {
  display: flex;
  flex-direction: column;
  gap: 10px;
  border-top: 1px solid var(--border);
  padding-top: 12px;
}
.filter-cluster-group, .filter-status-group {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
}
.filter-label { font-size: 12px; font-weight: 600; width: 64px; flex-shrink: 0; }
.pill-btn { font-size: 11px; padding: 4px 10px; border-radius: 6px; }

.orgs-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;
}
.org-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
  cursor: pointer;
  transition: all 0.15s ease;
  overflow: hidden;
}
.org-card:hover {
  transform: translateY(-2px);
  border-color: var(--accent);
  box-shadow: var(--shadow-lg);
}

.card-header {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.card-tags {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 6px;
  width: 100%;
}
.cluster-tag {
  max-width: 65%;
  overflow: hidden;
  text-overflow: ellipsis;
}
.status-tag {
  flex-shrink: 0;
}
.org-title {
  font-size: 15px;
  font-weight: 700;
  margin: 0;
  line-height: 1.35;
}
.org-full { font-size: 12px; line-height: 1.4; margin: 0; }

.plan-mini { display: flex; flex-direction: column; gap: 4px; }
.plan-mini-labels { display: flex; justify-content: space-between; font-size: 11px; }
.track { height: 5px; background: var(--raised); border-radius: 999px; overflow: hidden; }
.fill { height: 100%; border-radius: 999px; }

.metrics-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  background: var(--raised);
  padding: 10px;
  border-radius: 8px;
}
.m-cell { display: flex; flex-direction: column; gap: 2px; }
.m-key { font-size: 11px; color: var(--muted); }
.m-val { font-size: 13px; font-weight: 700; color: var(--text-primary); }

.card-footer {
  display: flex;
  justify-content: flex-end;
  border-top: 1px solid var(--border);
  padding-top: 8px;
  margin-top: auto;
}
.view-hint { font-size: 12px; font-weight: 600; color: var(--accent); }

.empty-state { text-align: center; padding: 40px; grid-column: 1 / -1; }

@media (max-width: 680px) {
  .orgs-grid {
    grid-template-columns: 1fr;
    gap: 12px;
  }
}
</style>
