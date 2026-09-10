import { createRouter, createWebHistory } from 'vue-router'

// Route-level lazy loading (bundle-split plan): each view becomes its own
// chunk, so demo fixtures never ship in the entry bundle and /app visitors
// never download the home page's CSS.
const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@/home/HomeView.vue')
    },
    {
      path: '/app',
      name: 'app',
      component: () => import('@/views/MainView.vue')
    },
    {
      path: '/demo',
      name: 'demo',
      component: () => import('@/demo/DemoView.vue')
    }
  ]
})

export default router
