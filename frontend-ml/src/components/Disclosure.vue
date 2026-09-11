<script setup>
/**
 * Раскрывающийся блок для технических подробностей.
 *
 * Приём простой: жюри и руководитель читают вывод, специалист разворачивает
 * методику. Так на экране не остаётся терминов, которые ничего не объясняют
 * тому, кто видит дашборд впервые.
 */
import { ref } from 'vue'

defineProps({
  label: { type: String, default: 'Как это посчитано' },
})

const open = ref(false)
</script>

<template>
  <div class="disclosure">
    <button class="toggle" :aria-expanded="open" @click="open = !open">
      <span class="chevron" :class="{ open }">›</span>
      {{ label }}
    </button>
    <div v-if="open" class="body">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.disclosure { margin-top: 14px; }
.toggle {
  border: none;
  padding: 4px 0;
  font-size: 12px;
  color: var(--muted);
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.toggle:hover { background: none; color: var(--text-secondary); }
.chevron { transition: transform 0.15s ease; display: inline-block; font-size: 15px; }
.chevron.open { transform: rotate(90deg); }
.body {
  margin-top: 10px;
  padding: 14px 16px;
  background: var(--plane);
  border: 1px solid var(--border);
  border-radius: 10px;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.6;
}
.body :deep(p + p) { margin-top: 8px; }
.body :deep(b) { color: var(--text-primary); font-weight: 600; }
</style>
