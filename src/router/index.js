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
    },
    {
      path: '/khong-gian/:id(\\d+)',
      name: 'khong-gian',
      component: () => import('@/views/SpaceView.vue')
    }
  ]
})

export default router
