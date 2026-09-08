import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
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
