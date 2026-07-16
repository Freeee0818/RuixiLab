<script setup>
import AppHeader from './components/AppHeader.vue'
import AppFooter from './components/AppFooter.vue'
</script>

<template>
  <div class="app-wrapper">
    <AppHeader />
    <main class="app-main">
      <router-view />
    </main>
    <AppFooter />
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

@media (max-width: 720px) {
  .app-main {
    padding-top: 98px;
  }
}
</style>
