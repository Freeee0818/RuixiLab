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
      <div class="header-actions">
        <router-link to="/" class="nav-item">首页</router-link>
        <router-link to="/analysis" class="nav-item">分析</router-link>
      </div>
    </div>
  </header>
</template>

<script>
export default {
  name: 'AppHeader'
};
</script>

<style scoped>
.app-header {
  background: #ffffff;
  border-bottom: 1px solid #e5e7eb;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  padding: 12px 0;
}

.header-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 24px;
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
  height: 60px;
  width: auto;
  object-fit: contain;
  border-radius: 4px;
}

.logo-text {
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.logo-title {
  font-size: 16px;
  font-weight: 600;
  color: #1e40af;
  line-height: 1.4;
  margin-bottom: 2px;
}

.logo-subtitle {
  font-size: 11px;
  color: #3b82f6;
  font-weight: 500;
  letter-spacing: 0.5px;
  line-height: 1.3;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 24px;
}

.nav-item {
  color: #4b5563;
  text-decoration: none;
  font-size: 15px;
  font-weight: 500;
  transition: color 0.2s;
  padding: 8px 0;
  position: relative;
}

.nav-item:hover {
  color: #1e40af;
}

.nav-item.router-link-active {
  color: #1e40af;
}

.nav-item.router-link-active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: #1e40af;
  border-radius: 2px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .header-container {
    padding: 0 16px;
  }

  .logo-image {
    height: 50px;
  }

  .logo-title {
    font-size: 14px;
  }

  .logo-subtitle {
    font-size: 10px;
  }

  .header-actions {
    gap: 16px;
  }

  .nav-item {
    font-size: 14px;
  }
}

@media (max-width: 480px) {
  .logo-text {
    display: none;
  }

  .logo-image {
    height: 45px;
  }

  .header-actions {
    gap: 12px;
  }
}
</style>

