import { createRouter, createWebHistory } from 'vue-router'
import Layout from '@/views/Layout.vue'
import OrderPaste from '@/views/phase1/OrderPaste.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: Layout,
      children: [
        {
          path: '',
          redirect: '/order-paste'
        },
        {
          path: 'order-paste',
          name: 'OrderPaste',
          component: OrderPaste,
          meta: { title: '订单粘贴解析' }
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