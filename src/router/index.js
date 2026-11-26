import { createRouter, createWebHistory } from "vue-router";
import {
  accessControlEnabled,
  accessState,
  refreshAccessSession,
} from "@/utils/access";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/",
      name: "cover",
      component: () => import("@/views/cover/index.vue"),
    },
    {
      path: "/analysis",
      name: "analysis",
      component: () => import("@/views/analysis/index.vue"),
    },
    {
      path: "/data-collection",
      name: "data-collection",
      component: () => import("@/views/DataCollectionView.vue"),
    },
    {
      path: "/access",
      name: "access",
      component: () => import("@/views/AccessView.vue"),
      meta: { public: true, hideShell: true },
    },
    {
      path: "/admin/access",
      name: "access-admin",
      component: () => import("@/views/AdminAccountsView.vue"),
      meta: { requiresAdmin: true },
    },
    {
      path: "/admin/classes",
      name: "class-admin",
      component: () => import("@/views/ClassManagementView.vue"),
      meta: { requiresAdmin: true },
    },
    // 兼容旧路由（可选）
    {
      path: "/symbolic-regression",
      redirect: "/analysis",
    },
  ],
});

router.beforeEach(async (to) => {
  if (!accessControlEnabled) return true;

  await refreshAccessSession();
  if (to.meta.public) {
    if (accessState.authenticated && to.name === "access") {
      const redirect = typeof to.query.redirect === "string" && to.query.redirect.startsWith("/")
        ? to.query.redirect
        : "/";
      return redirect;
    }
    return true;
  }

  if (!accessState.authenticated) {
    return {
      name: "access",
      query: { redirect: to.fullPath },
    };
  }
  if (to.meta.requiresAdmin && !accessState.isAdmin) return "/";
  return true;
});

export default router;
