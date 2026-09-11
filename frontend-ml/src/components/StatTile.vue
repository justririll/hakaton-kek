<script setup>
/** Плитка показателя: подпись, значение, необязательная сноска. */
defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], required: true },
  note: { type: String, default: '' },
  hero: { type: Boolean, default: false },
})
</script>

<template>
  <div class="tile">
    <div class="label">{{ label }}</div>
    <!-- Пропорциональные цифры: у крупных чисел моноширинные выглядят рыхло. -->
    <div class="value" :class="{ hero }">{{ value }}</div>
    <div v-if="note" class="note">{{ note }}</div>
  </div>
</template>

<style scoped>
.tile {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 16px 18px;
  box-shadow: var(--shadow);
}
.label { font-size: 12px; color: var(--muted); margin-bottom: 6px; }
.value { font-size: 26px; font-weight: 600; letter-spacing: -0.02em; line-height: 1.15; }
.value.hero { font-size: 48px; }
.note { font-size: 12px; color: var(--text-secondary); margin-top: 6px; }
</style>
