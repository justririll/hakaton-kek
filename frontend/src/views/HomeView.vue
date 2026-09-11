<script setup lang="ts">
import { onMounted } from 'vue'

import { useAnalyticsStore } from '@/stores/analytics'

const analytics = useAnalyticsStore()

onMounted(() => analytics.loadDashboard())
</script>

<template>
  <main class="dashboard">
    <section v-if="analytics.isLoading" class="state-card">Загружаем данные аналитики…</section>

    <section v-else-if="analytics.error" class="state-card state-card--error">
      <div>
        <strong>Не удалось получить данные</strong>
        <p>{{ analytics.error }}</p>
      </div>
      <button type="button" @click="analytics.loadDashboard">Повторить</button>
    </section>

    <template v-else-if="analytics.dashboard">
      <section class="metric-grid" aria-label="Основные показатели">
        <article class="metric-card">
          <span>Посетителей</span>
          <strong>{{ analytics.dashboard.metrics.total_attendees.toLocaleString('ru-RU') }}</strong>
          <small>{{ analytics.dashboard.metrics.algorithm_used }}</small>
        </article>
        <article class="metric-card">
          <span>Прогноз посещаемости</span>
          <strong>{{ analytics.dashboard.metrics.optimized_attendance_rate }}%</strong>
          <small>Было {{ analytics.dashboard.metrics.initial_attendance_rate }}%</small>
        </article>
        <article class="metric-card metric-card--accent">
          <span>Ожидаемый рост</span>
          <strong>+{{ analytics.dashboard.metrics.growth_percent }}%</strong>
          <small>Silhouette {{ analytics.dashboard.metrics.silhouette_score }}</small>
        </article>
      </section>

      <section class="panel">
        <div class="section-heading">
          <div>
            <span class="eyebrow">Аудитория</span>
            <h2>Кластеры посетителей</h2>
          </div>
          <span>{{ analytics.dashboard.clusters.length }} сегмента</span>
        </div>

        <div class="cluster-grid">
          <article
            v-for="cluster in analytics.dashboard.clusters"
            :key="cluster.id"
            class="cluster-card"
            :style="{ '--cluster-color': cluster.color }"
          >
            <div class="cluster-topline">
              <span class="cluster-tag">{{ cluster.tag }}</span>
              <strong>{{ cluster.share_percent }}%</strong>
            </div>
            <h3>{{ cluster.name }}</h3>
            <p>{{ cluster.count }} посетителей</p>
            <ul>
              <li v-for="interest in cluster.key_interests" :key="interest">{{ interest }}</li>
            </ul>
          </article>
        </div>
      </section>

      <section class="content-grid">
        <article class="panel">
          <div class="section-heading">
            <div>
              <span class="eyebrow">Программа</span>
              <h2>Расписание</h2>
            </div>
          </div>
          <div class="schedule-list">
            <div v-for="event in analytics.dashboard.schedule" :key="event.id" class="schedule-row">
              <time>{{ event.optimized_time_slot }}</time>
              <div>
                <strong>{{ event.title }}</strong>
                <span>{{ event.hall }}</span>
              </div>
              <span v-if="event.has_conflict" class="conflict">Оптимизировано</span>
            </div>
          </div>
        </article>

        <article class="panel recommendation-panel">
          <div class="section-heading">
            <div>
              <span class="eyebrow">AI-рекомендации</span>
              <h2>Что улучшить</h2>
            </div>
          </div>
          <div
            v-for="recommendation in analytics.dashboard.recommendations"
            :key="recommendation.event_id"
            class="recommendation"
          >
            <span>{{ recommendation.action }}</span>
            <h3>{{ recommendation.event_title }}</h3>
            <p>{{ recommendation.reason }}</p>
            <strong>{{ recommendation.impact }}</strong>
          </div>
        </article>
      </section>
    </template>
  </main>
</template>

<style scoped>
.dashboard {
  display: grid;
  gap: 1.25rem;
}

.metric-grid,
.cluster-grid,
.content-grid {
  display: grid;
  gap: 1rem;
}

.metric-grid {
  grid-template-columns: repeat(3, 1fr);
}

.metric-card,
.panel,
.state-card {
  border: 1px solid #e5e9f2;
  border-radius: 1rem;
  background: #fff;
  box-shadow: 0 12px 35px rgb(25 42 72 / 6%);
}

.metric-card {
  display: grid;
  gap: 0.2rem;
  padding: 1.4rem;
}

.metric-card span,
.metric-card small,
.cluster-card p,
.schedule-row span {
  color: #667085;
}

.metric-card strong {
  color: #17213a;
  font-size: 2rem;
}

.metric-card--accent {
  color: #fff;
  border: 0;
  background: linear-gradient(135deg, #455ecc, #7a55d5);
}

.metric-card--accent span,
.metric-card--accent small,
.metric-card--accent strong {
  color: #fff;
}

.panel,
.state-card {
  padding: clamp(1rem, 3vw, 1.5rem);
}

.section-heading,
.cluster-topline,
.state-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.section-heading {
  margin-bottom: 1.25rem;
}

.section-heading h2,
.cluster-card h3,
.recommendation h3 {
  margin: 0;
  color: #17213a;
}

.section-heading > span {
  color: #667085;
  font-size: 0.85rem;
}

.cluster-grid {
  grid-template-columns: repeat(4, 1fr);
}

.cluster-card {
  padding: 1rem;
  border-top: 3px solid var(--cluster-color);
  border-radius: 0.75rem;
  background: #f8f9fc;
}

.cluster-topline strong {
  color: var(--cluster-color);
  font-size: 1.35rem;
}

.cluster-tag,
.conflict,
.recommendation > span {
  display: inline-flex;
  width: fit-content;
  padding: 0.3rem 0.55rem;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 650;
}

.cluster-tag {
  color: var(--cluster-color);
  background: color-mix(in srgb, var(--cluster-color) 10%, white);
}

.cluster-card h3 {
  min-height: 3rem;
  margin-top: 0.9rem;
  font-size: 1rem;
}

.cluster-card p {
  margin: 0.35rem 0 0.8rem;
  font-size: 0.8rem;
}

.cluster-card ul {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.cluster-card li {
  padding: 0.25rem 0.45rem;
  border: 1px solid #e3e7ef;
  border-radius: 0.35rem;
  color: #475467;
  background: #fff;
  font-size: 0.7rem;
}

.content-grid {
  grid-template-columns: minmax(0, 1.6fr) minmax(280px, 1fr);
}

.schedule-list {
  display: grid;
}

.schedule-row {
  display: grid;
  grid-template-columns: 8rem 1fr auto;
  align-items: center;
  gap: 1rem;
  padding: 0.85rem 0;
  border-top: 1px solid #edf0f5;
}

.schedule-row:first-child {
  border-top: 0;
}

.schedule-row time {
  color: #455ecc;
  font-size: 0.8rem;
  font-weight: 700;
}

.schedule-row div {
  display: grid;
  gap: 0.2rem;
}

.schedule-row div span {
  font-size: 0.76rem;
}

.conflict {
  color: #a15c00 !important;
  background: #fff4db;
}

.recommendation-panel {
  color: #fff;
  border: 0;
  background: #17213a;
}

.recommendation-panel h2,
.recommendation h3 {
  color: #fff;
}

.recommendation > span {
  color: #bec9ff;
  background: rgb(117 139 239 / 16%);
}

.recommendation p {
  color: #b8c1d8;
  line-height: 1.6;
}

.recommendation > strong {
  color: #7fe4b5;
}

.state-card--error {
  border-color: #f3c2c2;
  color: #861f1f;
}

.state-card p {
  margin: 0.25rem 0 0;
}

button {
  padding: 0.65rem 1rem;
  border: 0;
  border-radius: 0.65rem;
  color: #fff;
  background: #455ecc;
  cursor: pointer;
}

@media (max-width: 960px) {
  .cluster-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .content-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .metric-grid,
  .cluster-grid {
    grid-template-columns: 1fr;
  }

  .schedule-row {
    grid-template-columns: 1fr;
    gap: 0.25rem;
  }
}
</style>
