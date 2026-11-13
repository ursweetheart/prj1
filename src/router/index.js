import { createRouter, createWebHistory } from 'vue-router'
import { APPROVERS, EDITORS, SALES, hasRole, loadUser, session } from '@/api'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/HomeView.vue')
    },
    {
      path: '/du-an',
      name: 'du-an-list',
      component: () => import('@/views/ProjectsView.vue')
    },
    // Mục "Không gian": tìm không gian tương tự bằng AI (cần backend)
    { path: '/khong-gian', name: 'khong-gian-list', component: () => import('@/views/SpacesView.vue') },
    { path: '/bo-suu-tap', name: 'bo-suu-tap', component: () => import('@/views/CollectionView.vue') },
    { path: '/bo-suu-tap/xem/:ma', name: 'bo-suu-tap-xem', component: () => import('@/views/CollectionView.vue') },
    { path: '/cong-trinh', redirect: to => ({ path: '/khong-gian', hash: to.hash }) },
    {
      path: '/du-an/:slug',
      name: 'du-an',
      component: () => import('@/views/ProjectView.vue')
    },
    {
      path: '/khong-gian/:id(\\d+)',
      name: 'khong-gian',
      component: () => import('@/views/SpaceView.vue')
    },
    { path: '/dang-nhap', name: 'dang-nhap', component: () => import('@/views/LoginView.vue') },
    { path: '/quan-tri', name: 'quan-tri', meta: { roles: EDITORS }, component: () => import('@/views/ReviewView.vue') },
    { path: '/quan-tri/phan-loai', name: 'phan-loai', meta: { roles: APPROVERS }, component: () => import('@/views/TaxonomyView.vue') },
    { path: '/khach-hang', name: 'khach-hang', meta: { roles: SALES }, component: () => import('@/views/LeadsView.vue') }
  ],
  // Trang mới: lên đầu trang; chỉ đổi hash bộ lọc (#loai=…) trên cùng trang: giữ nguyên;
  // hash là id phần tử (#du-an): cuộn tới đó, chừa chỗ cho header cố định.
  scrollBehavior(to, from, saved) {
    if (saved) return saved
    if (to.path === from.path) return false
    if (/^#[\w-]+$/.test(to.hash)) return { el: to.hash, top: 110 }
    return { top: 0 }
  }
})

// Pages with meta.roles need a signed-in user with one of those roles (the API enforces it again)
router.beforeEach(async to => {
  if (!to.meta.roles) return true
  if (session.token && !session.user) await loadUser()
  if (!session.user) return { name: 'dang-nhap', query: { next: to.fullPath } }
  return hasRole(to.meta.roles) || '/'
})

export default router
