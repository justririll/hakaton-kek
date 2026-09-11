<script setup>
import { onMounted, onBeforeUnmount } from "vue"
import Icon from "./Icon.vue"
import AiBriefCard from "./AiBriefCard.vue"
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
          <div class="header-top-row">
            <span class="badge badge-accent">Служебная аналитическая записка</span>
            <button class="close-btn mobile-only-close" @click="emit('close')" title="Закрыть">
              <Icon name="x" :size="18" />
            </button>
          </div>
          <h2>Сводный управленческий бриф сети центров</h2>
        </div>
        <div class="actions">
          <button class="btn-primary btn-print" @click="printReport">
            <Icon name="printer" :size="14" />
            <span>Распечатать / PDF</span>
          </button>
          <button class="close-btn desktop-only-close" @click="emit('close')" title="Закрыть">
            <Icon name="x" :size="16" />
          </button>
        </div>
      </div>

      <div class="modal-body">
        <div class="report-header">
          <h1>Аналитический бриф: Сеть центров прототипирования РФ</h1>
          <p class="muted">
            Отчётный период: 9 месяцев 2026 г. • Охват: {{ overview.organizations }} организаций высшего образования в сфере культуры
          </p>
        </div>

        <!-- Генеративное исполнительское резюме Gemini 3.6 Flash -->
        <AiBriefCard :compact="false" />

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
              <strong class="m-value">{{ overview.organizations - overview.plan_at_risk }} / {{ overview.organizations }}</strong>
              <small class="muted">центров в графике</small>
            </div>
          </div>
        </div>

        <div class="report-section">
          <h3>2. Аудиторные модели работы (5 архетипов)</h3>
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
                  <td class="mono-nums">{{ p.size }}</td>
                  <td>{{ p.summary }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="report-section">
          <h3>3. Оценка резерва сети (AI-рекомендации)</h3>
          <p class="section-desc">
            Приведение отстающих центров к стандартам лучших в своём архетипе обеспечивает прирост без дополнительных бюджетных вливаний:
          </p>
          <div class="impact-grid">
            <div class="impact-box">
              <span class="impact-plus">+{{ compact(overview.recommendations?.impact?.participants?.total) }}</span>
              <span class="impact-title">дополнительных участников (+40%)</span>
              <p class="muted">за счёт наполняемости существующих мастер-классов</p>
            </div>
            <div class="impact-box">
              <span class="impact-plus">+{{ compact(overview.recommendations?.impact?.products?.total) }}</span>
              <span class="impact-title">готовых арт-продуктов (+68%)</span>
              <p class="muted">за счёт добавления проектных воркшопов к лекциям</p>
            </div>
            <div class="impact-box">
              <span class="impact-plus">+{{ money(overview.recommendations?.impact?.revenue?.total) }}</span>
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
.header-top-row { display: flex; align-items: center; gap: 8px; }
.mobile-only-close { display: none; }
.desktop-only-close { display: inline-flex; align-items: center; justify-content: center; }
.actions { display: flex; align-items: center; gap: 8px; }
.btn-print { display: inline-flex; align-items: center; gap: 6px; white-space: nowrap; }

.report-header { border-bottom: 1px solid var(--border); padding-bottom: 16px; }
.report-header h1 { font-size: 18px; font-weight: 700; }
.report-section { display: flex; flex-direction: column; gap: 8px; margin-top: 8px; }
.report-section h3 { font-size: 14px; color: var(--accent); font-weight: 700; }
.section-desc { font-size: 13px; margin: 0; }

.metrics-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 10px;
}
.m-card {
  background: var(--raised);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.m-label { font-size: 11px; color: var(--muted); text-transform: uppercase; }
.m-value { font-size: 18px; font-weight: 700; color: var(--text-primary); font-variant-numeric: tabular-nums; }

.clusters-table-wrap {
  width: 100%;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  border-radius: 8px;
  border: 1px solid var(--border);
}
.report-table { width: 100%; min-width: 460px; border-collapse: collapse; font-size: 13px; }
.report-table th, .report-table td { padding: 8px 12px; border: 1px solid var(--border); }
.report-table th { background: var(--raised); }

.impact-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}
.impact-box {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.impact-plus { font-size: 20px; font-weight: 700; color: var(--success); font-variant-numeric: tabular-nums; }
.impact-title { font-weight: 600; font-size: 13px; }

.action-plan { padding-left: 20px; margin: 0; font-size: 13px; display: flex; flex-direction: column; gap: 6px; }
.report-footer { border-top: 1px solid var(--border); padding-top: 12px; margin-top: 14px; font-size: 11px; text-align: center; }

@media (max-width: 680px) {
  .modal-header {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
    padding: 12px 14px;
  }
  .header-info {
    width: 100%;
    gap: 6px;
  }
  .header-top-row {
    justify-content: space-between;
    width: 100%;
  }
  .mobile-only-close {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 4px 6px;
  }
  .desktop-only-close {
    display: none !important;
  }
  .header-info h2 {
    font-size: 15px;
    line-height: 1.3;
    margin: 0;
  }
  .actions {
    width: 100%;
  }
  .btn-print {
    width: 100%;
    justify-content: center;
    padding: 9px 14px;
    font-size: 13px;
    font-weight: 600;
  }
  .report-header h1 {
    font-size: 15px;
    line-height: 1.35;
  }
  .metrics-row {
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }
  .m-card {
    padding: 9px 10px;
  }
  .m-value {
    font-size: 15px;
  }
  .m-label {
    font-size: 10px;
  }
  .impact-grid {
    grid-template-columns: 1fr;
    gap: 8px;
  }
  .impact-box {
    padding: 10px 12px;
  }
  .action-plan {
    padding-left: 18px;
    font-size: 12px;
  }
}

@media print {
  .no-print { display: none !important; }
  .modal-overlay { position: static; background: none; padding: 0; }
  .modal-container { box-shadow: none; border: none; max-width: 100%; max-height: 100%; }
}
</style>
