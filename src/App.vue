<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from './components/AppHeader.vue'
import AppFooter from './components/AppFooter.vue'

const route = useRoute()
const hideShell = computed(() => Boolean(route.meta.hideShell))
</script>

<template>
  <div class="app-wrapper">
    <AppHeader v-if="!hideShell" />
    <main :class="['app-main', { 'app-main--standalone': hideShell }]">
      <router-view />
    </main>
    <AppFooter v-if="!hideShell" />
  </div>
</template>

<style>
.app-wrapper {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #ffffff;
}

.app-main {
  flex: 1;
  width: 100%;
  padding-top: 69px;
}

.app-main--standalone {
  padding-top: 0;
}

@media (max-width: 720px) {
  .app-main {
    padding-top: 98px;
  }
}
</style>
