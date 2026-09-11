<script setup>
import { onMounted, onBeforeUnmount } from "vue"
import { compact, money, percent } from "../theme"

const props = defineProps({
  overview: { type: Object, required: true },
  clusters: { type: Object, required: true },
  plan: { type: Array, required: true },
})

const emit = defineEmits(["close"])

function printReport() {
  window.print()
}

function onKeydown(e) {
  if (e.key === "Escape") emit("close")
}

onMounted(() => window.addEventListener("keydown", onKeydown))
onBeforeUnmount(() => window.removeEventListener("keydown", onKeydown))
</script>

<template>
  <div class="modal-overlay" @click.self="emit('close')">
    <div class="modal-container print-area">
      <div class="modal-header no-print">
        <div class="header-info">
          <span class="badge badge-accent">Экспресс-отчет для руководства</span>
          <h2>Сводный управленческий бриф сети центров</h2>
        </div>
        <div class="actions">
          <button class="btn-primary" @click="printReport">🖨️ Распечатать / В PDF</button>
          <button class="close-btn" @click="emit('close')">✕</button>
        </div>
      </div>

      <div class="modal-body">
        <div class="report-header">
          <h1>Аналитическая справка: Сеть центров прототипирования</h1>
          <p class="muted">
            Отчётный период: 9 месяцев 2026 г. • Охват: {{ overview.organizations }} организаций высшего образования в сфере культуры
          </p>
        </div>

        <div class="report-section">
          <h3>1. Ключевые результаты сети</h3>
          <div class="metrics-row">
            <div class="m-card">
              <span class="m-label">Аудитория (факт)</span>
              <strong class="m-value">{{ compact(overview.audience_total) }}</strong>
              <small class="muted">человек обучено</small>
            </div>
            <div class="m-card">
              <span class="m-label">Творческие продукты</span>
              <strong class="m-value">{{ compact(overview.products_total) }}</strong>
              <small class="muted">{{ overview.median_product_rate }} на участника</small>
            </div>
            <div class="m-card">
              <span class="m-label">Объём платных услуг</span>
              <strong class="m-value">{{ money(overview.revenue_total) }}</strong>
              <small class="muted">заработанные средства</small>
            </div>
            <div class="m-card">
              <span class="m-label">Выполнение плана года</span>
              <strong class="m-value">{{ overview.organizations - overview.plan_at_risk }}/{{ overview.organizations }}</strong>
              <small class="muted">центров в графике</small>
            </div>
          </div>
        </div>

        <div class="report-section">
          <h3>2. Аудиторные модели работы (5 кластеров)</h3>
          <p class="section-desc">
            Центры разделены по структуре аудитории, форматам обучения и глубине сопровождения:
          </p>
          <div class="clusters-table-wrap">
            <table class="report-table">
              <thead>
                <tr>
                  <th>Модель (Архетип)</th>
                  <th>Число центров</th>
                  <th>Ключевая специфика</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="p in clusters.profiles" :key="p.cluster_id">
                  <td><b>{{ p.name }}</b></td>
                  <td>{{ p.size }}</td>
                  <td>{{ p.summary }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="report-section">
          <h3>3. Оценка скрытого резерва сети (AI-рекомендации)</h3>
          <p class="section-desc">
            Приведение отстающих центров к стандартам лучших в своём кластере обеспечивает прирост без дополнительных бюджетных вливаний:
          </p>
          <div class="impact-grid">
            <div class="impact-box">
              <span class="impact-plus">+{{ compact(overview.recommendations.impact.participants?.total) }}</span>
              <span class="impact-title">дополнительных участников (+40%)</span>
              <p class="muted">за счёт наполняемости существующих мастер-классов</p>
            </div>
            <div class="impact-box">
              <span class="impact-plus">+{{ compact(overview.recommendations.impact.products?.total) }}</span>
              <span class="impact-title">готовых арт-продуктов (+68%)</span>
              <p class="muted">за счёт добавления проектных воркшопов к лекциям</p>
            </div>
            <div class="impact-box">
              <span class="impact-plus">+{{ money(overview.recommendations.impact.revenue?.total) }}</span>
              <span class="impact-title">дополнительной выручки (+38%)</span>
              <p class="muted">за счёт платных специализированных модулей</p>
            </div>
          </div>
        </div>

        <div class="report-section">
          <h3>4. План действий на IV квартал 2026 года</h3>
          <ol class="action-plan">
            <li><b>Снять риски по 7 отстающим центрам:</b> увеличить среднемесячную частоту проведения мероприятий до нормативной.</li>
            <li><b>Трансформировать формат массовых лекций:</b> ввести обязательный защитный творческий проект для повышения конверсии в продукты.</li>
            <li><b>Масштабировать опыт лидеров кластера «Продуктовые мастерские»:</b> распространить методику на открытые городские площадки.</li>
          </ol>
        </div>

        <div class="report-footer">
          <p class="muted">
            Культурный Пульс • Аналитическая платформа центров прототипирования РФ • Сгенерировано автоматически
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.header-info { display: flex; flex-direction: column; gap: 4px; }
.actions { display: flex; align-items: center; gap: 12px; }
.report-header { border-bottom: 2px solid var(--border); padding-bottom: 16px; }
.report-header h1 { font-size: 20px; font-weight: 700; }
.report-section { display: flex; flex-direction: column; gap: 10px; margin-top: 10px; }
.report-section h3 { font-size: 15px; color: var(--accent); }
.section-desc { font-size: 13px; margin: 0; }

.metrics-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
}
.m-card {
  background: var(--raised);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.m-label { font-size: 11px; color: var(--muted); text-transform: uppercase; }
.m-value { font-size: 20px; font-weight: 700; color: var(--text-primary); }

.report-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.report-table th, .report-table td { padding: 8px 12px; border: 1px solid var(--border); }
.report-table th { background: var(--raised); }

.impact-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 14px;
}
.impact-box {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.impact-plus { font-size: 22px; font-weight: 700; color: var(--success); }
.impact-title { font-weight: 600; font-size: 13px; }

.action-plan { padding-left: 20px; margin: 0; font-size: 13px; display: flex; flex-direction: column; gap: 6px; }
.report-footer { border-top: 1px solid var(--border); padding-top: 12px; margin-top: 16px; font-size: 11px; text-align: center; }

@media print {
  .no-print { display: none !important; }
  .modal-overlay { position: static; background: none; padding: 0; }
  .modal-container { box-shadow: none; border: none; max-width: 100%; max-height: 100%; }
}
</style>
