import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/HomeView.vue'),
  },
  {
    path: '/simulate/:id',
    name: 'simulate',
    component: () => import('@/views/SimulateView.vue'),
  },
  {
    path: '/report/:id',
    name: 'report',
    component: () => import('@/views/ReportView.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
