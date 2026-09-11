<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>

<template>
  <div class="app-shell">
    <header class="app-header">
      <div>
        <span class="eyebrow">Culture Insights</span>
        <h1>Аналитика учреждений культуры</h1>
      </div>
      <span class="api-status">API · FastAPI</span>
    </header>

    <div class="app-content">
      <RouterView />
    </div>
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 2rem;
  padding: 1.4rem clamp(1rem, 4vw, 4rem);
  color: #fff;
  background: #17213a;
}

.app-header h1 {
  margin: 0.15rem 0 0;
  font-size: clamp(1.25rem, 3vw, 1.8rem);
  font-weight: 650;
}

.eyebrow {
  color: #9cafe7;
  font-size: 0.7rem;
  font-weight: 750;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.api-status {
  flex: 0 0 auto;
  padding: 0.45rem 0.75rem;
  border: 1px solid rgb(255 255 255 / 18%);
  border-radius: 999px;
  color: #cbd5f3;
  font-size: 0.75rem;
}

.app-content {
  width: min(1280px, 100%);
  margin: 0 auto;
  padding: clamp(1rem, 4vw, 3rem);
}
</style>
