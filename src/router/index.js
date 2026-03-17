import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'cover',
      component: () => import('@/views/cover/index.vue'),
    },
    {
      path: '/analysis',
      name: 'analysis',
      component: () => import('@/views/analysis/index.vue'),
    },
    // 兼容旧路由（可选）
    {
      path: '/symbolic-regression',
      redirect: '/analysis',
    },
  ],
})

export default router
