<template>
  <aside class="chart-guide" aria-label="Как читать график">
    <h3>Как читать график</h3>
    <ul><slot /></ul>
  </aside>
</template>

<style scoped>
.chart-guide {
  margin: 12px 0 16px;
  padding: 14px 16px;
  border-radius: 10px;
  background: var(--accent-wash);
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.6;
}
h3 { color: var(--text-primary); font-size: 13px; }
ul { margin: 6px 0 0; padding-left: 20px; }
.chart-guide :deep(li + li) { margin-top: 5px; }
.chart-guide :deep(strong) { color: var(--text-primary); }
</style>
