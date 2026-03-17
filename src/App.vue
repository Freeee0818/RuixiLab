<script setup>
import AppHeader from './components/AppHeader.vue'
</script>

<template>
  <div class="app-wrapper">
    <AppHeader />
    <main class="app-main">
      <router-view />
    </main>
  </div>
</template>

<style>
body {
  margin: 0;
  padding: 0;
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #2c3e50;
}

.app-wrapper {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-main {
  flex: 1;
  width: 100%;
  padding-top: 85px; /* 导航栏高度 */
}
</style>
