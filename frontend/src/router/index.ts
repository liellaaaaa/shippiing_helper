import { createRouter, createWebHistory } from 'vue-router'
import Layout from '@/views/Layout.vue'
import Phase1Workflow from '@/views/phase1/Phase1Workflow.vue'
import OrderPaste from '@/views/phase1/OrderPaste.vue'
import PIExtract from '@/views/phase1/PIExtract.vue'
import DataMerge from '@/views/phase1/DataMerge.vue'
import PackageCalc from '@/views/phase1/PackageCalc.vue'
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
          path: 'order-paste',
          name: 'OrderPaste',
          component: OrderPaste,
          meta: { title: '订单粘贴解析' }
        },
        {
          path: 'pi-extract',
          name: 'PIExtract',
          component: PIExtract,
          meta: { title: 'PI 文件提取' }
        },
        {
          path: 'data-merge',
          name: 'DataMerge',
          component: DataMerge,
          meta: { title: '数据关联' }
        },
        {
          path: 'package-calc',
          name: 'PackageCalc',
          component: PackageCalc,
          meta: { title: '包装计算' }
        },
        {
          path: 'dashboard',
          name: 'Dashboard',
          component: Dashboard,
          meta: { title: '数据看板' }
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