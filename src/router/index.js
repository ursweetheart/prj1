import { createRouter, createWebHistory } from 'vue-router'
import { APPROVERS, SALES, STAFF, hasRole, loadUser, session } from '@/api'

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
    },
    {
      path: '/khong-gian/:id(\\d+)',
      name: 'khong-gian',
      component: () => import('@/views/SpaceView.vue')
    },
    { path: '/dang-nhap', name: 'dang-nhap', component: () => import('@/views/LoginView.vue') },
    { path: '/quan-tri', name: 'quan-tri', meta: { roles: STAFF }, component: () => import('@/views/ReviewView.vue') },
    { path: '/khach-hang', name: 'khach-hang', meta: { roles: SALES }, component: () => import('@/views/LeadsView.vue') }
  ]
})

// Pages with meta.roles need a signed-in user with one of those roles (the API enforces it again)
router.beforeEach(async to => {
  if (!to.meta.roles) return true
  if (session.token && !session.user) await loadUser()
  if (!session.user) return { name: 'dang-nhap', query: { next: to.fullPath } }
  return hasRole(to.meta.roles) || '/'
})

export default router
