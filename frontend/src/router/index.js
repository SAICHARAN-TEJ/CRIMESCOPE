import { createRouter, createWebHistory } from 'vue-router'

const LandingView = () => import('../views/LandingView.vue')
const AppView = () => import('../views/AppView.vue')
const NewSimulationView = () => import('../views/NewSimulationView.vue')
const NotFoundView = () => import('../views/NotFoundView.vue')

const routes = [
  {
    path: '/',
    name: 'Landing',
    component: LandingView,
    meta: { transition: 'fade' }
  },
  {
    path: '/app',
    name: 'App',
    component: AppView,
    meta: { transition: 'slide' },
    children: [
      { path: '', redirect: { name: 'AppOverview' } },
      { path: 'overview', name: 'AppOverview', meta: { tab: 'overview' } },
      { path: 'simulation', name: 'AppSimulation', meta: { tab: 'simulation' } },
      { path: 'agents', name: 'AppAgents', meta: { tab: 'agents' } },
      { path: 'report', name: 'AppReport', meta: { tab: 'report' } },
      { path: 'chat', name: 'AppChat', meta: { tab: 'chat' } }
    ]
  },
  {
    path: '/new',
    name: 'NewSimulation',
    component: NewSimulationView,
    meta: { transition: 'slide' }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: NotFoundView,
    meta: { transition: 'fade' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition
    return { top: 0, behavior: 'smooth' }
  }
})

export default router
