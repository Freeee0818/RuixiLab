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
        <router-link
          v-if="accessControlEnabled && accessState.isAdmin"
          to="/admin/access"
          class="nav-item"
        >账号管理</router-link>
        <router-link
          v-if="accessControlEnabled && accessState.isAdmin"
          to="/admin/classes"
          class="nav-item"
        >班级管理</router-link>
        <div v-if="accessControlEnabled" class="account-area">
          <span class="account-name">{{ accountLabel }}</span>
          <button
            v-if="accessState.source === 'account'"
            class="logout-button"
            type="button"
            @click="handleLogout"
          >退出</button>
        </div>
      </nav>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  accessControlEnabled,
  accessState,
  logoutAccess,
} from '@/utils/access'

const router = useRouter()
const accountLabel = computed(() => {
  if (accessState.source === 'campus') return '校园网访客'
  return accessState.displayName || accessState.username || '已登录'
})

async function handleLogout() {
  await logoutAccess()
  await router.push('/access')
}
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

.account-area {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-left: 18px;
  border-left: 1px solid var(--gl-border);
}

.account-name {
  max-width: 112px;
  overflow: hidden;
  color: var(--gl-text-secondary);
  font-size: 13px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.logout-button {
  padding: 6px 9px;
  border: 0;
  border-radius: 7px;
  color: var(--gl-primary);
  background: var(--gl-primary-soft);
  cursor: pointer;
}

@media (max-width: 900px) {
  .header-container {
    padding: 0 20px;
  }

  .header-actions {
    gap: 16px;
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

  .account-area {
    flex: 0 0 auto;
    padding-left: 12px;
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
