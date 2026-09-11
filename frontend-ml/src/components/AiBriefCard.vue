<script setup>
/**
 * Компонент AI-резюме сети (на базе Google Gemini 3.6 Flash).
 * Предоставляет руководству выжимку стратегического статуса,
 * точек роста и мер на IV квартал.
 */
import { onMounted, ref, computed } from "vue"
import { api } from "../api"
import Icon from "./Icon.vue"

const props = defineProps({
  compact: { type: Boolean, default: false },
})

const loading = ref(false)
const error = ref(null)
const summary = ref(null)

// Бэкенд помечает ответ status="fallback", когда Gemini не ответил и текст
// собран локально. Выдавать такой бриф за работу модели нельзя.
const isFallback = computed(() => summary.value?.status === "fallback")
const copied = ref(false)
const expanded = ref(!props.compact)

async function loadSummary(force = false) {
  loading.value = true
  error.value = null
  try {
    const res = await api.aiSummary(force)
    summary.value = res
  } catch (e) {
    error.value = e.message || "Не удалось получить AI-резюме"
  } finally {
    loading.value = false
  }
}

function copyText() {
  if (!summary.value?.content) return
  navigator.clipboard.writeText(summary.value.content)
  copied.value = true
  setTimeout(() => (copied.value = false), 2500)
}

/** Преобразование markdown в форматированные секции */
const parsedSections = computed(() => {
  if (!summary.value?.content) return []
  const text = summary.value.content
  const rawSections = text.split(/###\s+/).filter(Boolean)
  if (rawSections.length === 0 || !text.includes("###")) {
    return [{
      title: "Стратегический обзор сети",
      paragraphs: text.split("\n\n").filter(Boolean),
      items: [],
    }]
  }

  return rawSections.map((sec) => {
    const lines = sec.trim().split("\n")
    const title = lines[0].replace(/^[\d.]+\s*/, "").trim()
    const rest = lines.slice(1).join("\n").trim()

    const items = []
    const paras = []

    for (const line of rest.split("\n")) {
      const trimmed = line.trim()
      if (!trimmed || trimmed === "---") continue
      if (trimmed.startsWith("-") || trimmed.startsWith("*") || /^\d+\./.test(trimmed)) {
        items.push(trimmed.replace(/^[-*]\s+|\d+\.\s*/, ""))
      } else {
        paras.push(trimmed)
      }
    }

    return {
      title,
      paragraphs: paras,
      items,
    }
  })
})

function formatBold(str) {
  if (!str) return ""
  return str
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/g, "<em>$1</em>")
    .replace(/`(.*?)`/g, "<code>$1</code>")
}

onMounted(() => {
  loadSummary(false)
})
</script>

<template>
  <div class="card ai-card">
    <div class="ai-header">
      <div class="ai-branding">
        <div class="ai-icon-chip">
          <Icon name="sparkles" :size="16" />
        </div>
        <div>
          <div class="ai-title-row">
            <h3>Аналитическое резюме для руководства</h3>
            <span
              class="badge ai-model-badge"
              :class="isFallback ? 'badge-neutral' : 'badge-purple'"
              :title="isFallback ? (summary?.error || 'Модель недоступна') : summary?.model"
            >
              {{ isFallback ? "Расчётный бриф" : "AI-аналитика" }}
            </span>
          </div>
          <p class="muted ai-sub">
            <template v-if="isFallback">
              Модель недоступна — текст собран детерминированным алгоритмом на тех же числах
            </template>
            <template v-else>
              Сводный бриф по показателям и программированию 20 центров культуры
            </template>
          </p>
        </div>
      </div>

      <div class="ai-actions no-print">
        <button
          v-if="summary?.content"
          class="btn-copy"
          @click="copyText"
          :title="copied ? 'Скопировано!' : 'Скопировать текст'"
        >
          <Icon :name="copied ? 'check' : 'file-text'" :size="14" />
          <span>{{ copied ? 'Скопировано' : 'Копировать' }}</span>
        </button>

        <button
          class="btn-refresh"
          :disabled="loading"
          @click="loadSummary(true)"
          title="Обновить аналитическое резюме"
        >
          <Icon name="refresh-cw" :size="14" :class="{ spinning: loading }" />
          <span>{{ loading ? 'Анализ...' : 'Обновить' }}</span>
        </button>

        <button
          v-if="compact"
          class="btn-toggle"
          @click="expanded = !expanded"
        >
          <span>{{ expanded ? 'Свернуть' : 'Развернуть' }}</span>
        </button>
      </div>
    </div>

    <!-- Загрузка -->
    <div v-if="loading && !summary" class="ai-loading">
      <div class="ai-pulse-bar" />
      <span class="muted">Формирование аналитической записки по показателям сети...</span>
    </div>

    <!-- Ошибка -->
    <div v-else-if="error" class="ai-error">
      <Icon name="alert-triangle" :size="16" />
      <span>{{ error }}</span>
      <button class="btn-retry" @click="loadSummary(true)">Повторить</button>
    </div>

    <!-- Контент AI-брифа -->
    <div v-else-if="summary && expanded" class="ai-body">
      <div class="sections-container">
        <div
          v-for="(sec, idx) in parsedSections"
          :key="idx"
          class="ai-section"
        >
          <div class="sec-header">
            <span class="sec-index">{{ String(idx + 1).padStart(2, '0') }}</span>
            <h4>{{ sec.title }}</h4>
          </div>

          <div v-if="sec.paragraphs.length" class="sec-paragraphs">
            <p
              v-for="(p, pi) in sec.paragraphs"
              :key="pi"
              v-html="formatBold(p)"
            />
          </div>

          <ul v-if="sec.items.length" class="sec-bullets">
            <li
              v-for="(item, ii) in sec.items"
              :key="ii"
              v-html="formatBold(item)"
            />
          </ul>
        </div>
      </div>

      <!-- Подвал -->
      <div class="ai-footer muted">
        <span>Сформировано: {{ summary.generated_at }}</span>
      </div>
    </div>

    <!-- Краткий вид если свернуто -->
    <div v-else-if="summary && !expanded" class="ai-collapsed-preview" @click="expanded = true">
      <p class="preview-text">
        {{ parsedSections[0]?.paragraphs[0] || "Нажмите, чтобы раскрыть полный управленческий бриф." }}
      </p>
      <div class="preview-footer">
        <div class="preview-chips">
          <span v-for="sec in parsedSections" :key="sec.title" class="preview-chip">
            {{ sec.title }}
          </span>
        </div>
        <span class="view-more">
          Развернуть бриф
          <Icon name="chevron-right" :size="13" />
        </span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ai-card {
  background: var(--surface);
  border: 1px solid var(--border);
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.ai-card::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, var(--purple), color-mix(in srgb, var(--purple) 20%, transparent));
}

.ai-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 14px;
}
.ai-branding {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}
.ai-icon-chip {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: var(--purple-wash);
  color: var(--purple);
  display: grid;
  place-items: center;
  flex-shrink: 0;
  margin-top: 2px;
}
.ai-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.ai-title-row h3 {
  font-size: 16px;
  font-weight: 700;
  letter-spacing: -0.01em;
}
.ai-model-badge {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.03em;
}
.cache-badge { font-size: 10px; }
.ai-sub { font-size: 12px; margin-top: 2px; }

.ai-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.btn-copy, .btn-refresh, .btn-toggle {
  font-size: 12px;
  padding: 5px 10px;
  border-radius: 8px;
}
.btn-refresh:disabled { opacity: 0.6; cursor: not-allowed; }
.spinning { animation: spin 1s linear infinite; }
@keyframes spin {
  to { transform: rotate(360deg); }
}

.ai-loading {
  padding: 24px 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  font-size: 13px;
}
.ai-pulse-bar {
  height: 3px;
  border-radius: 2px;
  background: linear-gradient(90deg, transparent, var(--purple), transparent);
  animation: pulseBar 1.5s infinite linear;
}
@keyframes pulseBar {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

.ai-error {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--danger);
  font-size: 13px;
  padding: 12px;
  background: var(--danger-wash);
  border-radius: 8px;
}
.btn-retry { font-size: 11px; padding: 3px 8px; }

.ai-body {
  display: flex;
  flex-direction: column;
  gap: 18px;
  animation: fadeIn 0.2s ease;
}
.sections-container {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.ai-section {
  background: var(--raised);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.sec-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 2px;
}
.sec-index {
  font-family: monospace;
  font-size: 12px;
  font-weight: 700;
  color: var(--purple);
  background: var(--purple-wash);
  padding: 1px 6px;
  border-radius: 4px;
}
.sec-header h4 {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
}

.sec-paragraphs p {
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-primary);
  margin: 0;
}
.sec-paragraphs p + p { margin-top: 8px; }

.sec-bullets {
  margin: 4px 0 0 0;
  padding-left: 18px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.sec-bullets li {
  font-size: 13px;
  line-height: 1.5;
  color: var(--text-primary);
}

.ai-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  font-size: 11px;
  padding-top: 8px;
  border-top: 1px solid var(--border);
}
.ai-meta-left { display: flex; gap: 8px; flex-wrap: wrap; }

.ai-collapsed-preview {
  background: var(--raised);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px 16px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: border-color 0.15s ease;
}
.ai-collapsed-preview:hover { border-color: var(--purple); }
.preview-text {
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-secondary);
  /* Ограничение по строкам вместо nowrap: раньше фраза рвалась посреди слова. */
  display: -webkit-box;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin: 0;
}
.preview-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}
.preview-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.preview-chip {
  font-size: 11px;
  font-weight: 600;
  color: var(--muted);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 3px 9px;
}
.view-more {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 12px;
  font-weight: 600;
  color: var(--purple);
  white-space: nowrap;
}
</style>
