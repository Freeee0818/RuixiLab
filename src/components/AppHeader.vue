<template>
  <header class="app-header">
    <div class="header-container">
      <div class="logo-section">
        <img
          src="@/assets/BUPTPhyscis.jpg"
          alt="北京邮电大学物理科学与技术学院"
          class="logo-image"
        />
      </div>
      <nav class="header-actions" aria-label="主导航">
        <router-link to="/" class="nav-item">首页</router-link>
        <router-link to="/analysis" class="nav-item">分析工作台</router-link>
        <router-link to="/data-collection" class="nav-item">数据采集</router-link>
        <a href="http://10.161.25.80:8000" target="_blank" class="nav-item"
          >虚拟实验</a
        >
        <a
          href="http://t.zhihuishu.com/NaXDze0e"
          target="_blank"
          class="nav-item"
          >智慧课程</a
        >
      </nav>
    </div>
  </header>
</template>

<script>
export default {
  name: "AppHeader",
};
</script>

<style scoped>
.app-header {
  background: #ffffff;
  border-bottom: 1px solid var(--gl-border);
  box-shadow: 0 2px 12px rgba(31, 49, 82, 0.05);
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  height: 69px;
}

.header-container {
  width: min(100%, 1504px);
  height: 100%;
  margin: 0 auto;
  padding: 0 32px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logo-section {
  display: flex;
  align-items: center;
  gap: 16px;
}

.logo-image {
  width: min(390px, 38vw);
  height: 46px;
  width: auto;
  object-fit: contain;
  border-radius: 2px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 28px;
}

.nav-item {
  color: var(--gl-text-secondary);
  text-decoration: none;
  font-size: 14px;
  font-weight: 600;
  line-height: 1;
  transition: color 0.2s;
  padding: 27px 0 24px;
  white-space: nowrap;
  position: relative;
}

.nav-item:hover {
  color: var(--gl-primary);
}

.nav-item.router-link-active {
  color: var(--gl-primary);
}

.nav-item.router-link-active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--gl-primary);
  border-radius: 999px 999px 0 0;
}

@media (max-width: 900px) {
  .header-container {
    padding: 0 20px;
  }

  .header-actions {
    gap: 18px;
  }
}

@media (max-width: 720px) {
  .app-header {
    height: 98px;
  }

  .header-container {
    align-items: stretch;
    flex-direction: column;
    padding: 8px 16px 0;
  }

  .logo-section {
    min-height: 39px;
  }

  .logo-image {
    width: 230px;
    height: 34px;
  }

  .header-actions {
    width: 100%;
    gap: 24px;
    overflow-x: auto;
    scrollbar-width: none;
  }

  .header-actions::-webkit-scrollbar {
    display: none;
  }

  .nav-item {
    flex: 0 0 auto;
    padding: 15px 0 13px;
    font-size: 13px;
  }
}
</style>

