import { createRouter, createWebHistory } from 'vue-router'
import MainView from '@/views/MainView.vue'
import DemoView from '@/demo/DemoView.vue'
import HomeView from '@/home/HomeView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView
    },
    {
      path: '/app',
      name: 'app',
      component: MainView
    },
    {
      path: '/demo',
      name: 'demo',
      component: DemoView
    }
  ]
})

export default router
