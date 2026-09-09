import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/HomeView.vue')
    },
    {
      path: '/cong-trinh',
      name: 'cong-trinh',
      component: () => import('@/views/CongTrinhView.vue')
    }
  ]
})

export default router
