import { createRouter, createWebHistory } from 'vue-router'
import Layout from '@/views/Layout.vue'
import Phase1Workflow from '@/views/phase1/Phase1Workflow.vue'
import Phase2Workflow from '@/views/phase2/Phase2Workflow.vue'
import Dashboard from '@/views/phase1/Dashboard.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
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
        }
      ]
    }
  ]
})

router.beforeEach((to, _from, next) => {
  document.title = (to.meta.title as string || 'ShippingHelper') + ' - ShippingHelper'
  next()
})

export default router