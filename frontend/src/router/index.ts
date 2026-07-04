import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { trackEvent, flush } from '@/plugins/track'
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
        },
      ]
    }
  ]
})

// 当前所在模块（用于检测模块切换）
let currentModule: string | null = null

// 使用 RegExp 精确匹配，避免 /phase10 误匹配 /phase1
const moduleMap: Record<string, RegExp[]> = {
  'phase1': [/^\/workflow$/, /^\/$/],
  'phase2': [/^\/phase2/],
  'phase3': [/^\/phase3/],
  'dashboard': [/^\/dashboard/],
  'data-center': [/^\/data-center/],
}

function getModuleFromPath(path: string): string | null {
  for (const [module, patterns] of Object.entries(moduleMap)) {
    if (patterns.some(re => re.test(path))) return module
  }
  return null
}

router.beforeEach(async (to, _from, next) => {
  document.title = (to.meta.title as string || 'ShippingHelper') + ' - ShippingHelper'
  const authStore = useAuthStore()

  if (to.path === '/login') {
    if (authStore.isLoggedIn) {
      next('/workflow')
    } else {
      if (currentModule) {
        trackEvent({ event: 'exit_module', module: currentModule })
        currentModule = null
      }
      await flush()
      next()
    }
    return
  }

  if (!authStore.isLoggedIn) {
    next('/login')
    return
  }

  const toModule = getModuleFromPath(to.path)
  if (toModule && toModule !== currentModule) {
    if (currentModule) trackEvent({ event: 'exit_module', module: currentModule })
    trackEvent({ event: 'enter_module', module: toModule })
    currentModule = toModule
  }

  next()
})

export default router
