import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import Layout from '@/views/Layout.vue'
import Phase1Workflow from '@/views/phase1/Phase1Workflow.vue'
import Phase2Workflow from '@/views/phase2/Phase2Workflow.vue'
import Phase3Workflow from '@/views/phase3/Phase3Workflow.vue'
import Dashboard from '@/views/phase1/Dashboard.vue'
import DataCenter from '@/views/data-center/DataCenter.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/auth/Login.vue'),
      meta: { title: '登录', public: true }
    },
    {
      path: '/',
      component: Layout,
      children: [
        {
          path: '',
          redirect: '/workflow'
        },
        {
          path: 'workflow',
          name: 'Phase1Workflow',
          component: Phase1Workflow,
          meta: { title: '订单处理工作流' }
        },
        {
          path: 'dashboard',
          name: 'Dashboard',
          component: Dashboard,
          meta: { title: '数据看板' }
        },
        {
          path: 'phase2',
          name: 'Phase2Workflow',
          component: Phase2Workflow,
          meta: { title: '文档编辑' }
        },
        {
          path: 'phase3',
          name: 'Phase3Workflow',
          component: Phase3Workflow,
          meta: { title: '报关资料编辑' }
        },
        {
          path: 'data-center',
          name: 'DataCenter',
          component: DataCenter,
          meta: { title: '数据中心' }
        }
      ]
    }
  ]
})

router.beforeEach((to, _from, next) => {
  document.title = (to.meta.title as string || 'ShippingHelper') + ' - ShippingHelper'

  const authStore = useAuthStore()

  // 允许访问登录页
  if (to.path === '/login') {
    if (authStore.isLoggedIn) {
      next('/workflow')
    } else {
      next()
    }
    return
  }

  // 其他页面需要登录
  if (!authStore.isLoggedIn) {
    next('/login')
  } else {
    next()
  }
})

export default router