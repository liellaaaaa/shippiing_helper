import { App, Directive } from 'vue'
import { useAuthStore } from '@/stores/auth'

interface TrackOptions {
  event: string
  module?: string
  detail?: Record<string, unknown>
}

interface QueuedEvent {
  event_type: string
  user_name: string
  module?: string
  action_time: string
  detail?: string
  ip_address?: string
}

const eventQueue: QueuedEvent[] = []

function flush() {
  if (eventQueue.length === 0) return
  const events = eventQueue.splice(0)
  const payload = JSON.stringify({ events })

  // sendBeacon：异步发送，页面卸载时也能保证送达
  // sendBeacon 自动使用 text/plain;charset=UTF-8
  if (navigator.sendBeacon) {
    navigator.sendBeacon('/api/v1/audit/batch', payload)
  } else {
    // 降级：同步 fetch（页面卸载时可能不完成）
    fetch('/api/v1/audit/batch', {
      method: 'POST',
      body: payload,
      headers: { 'Content-Type': 'application/json' },
      keepalive: true,
    }).catch(() => {})
  }
}

function enqueueEvent(options: TrackOptions) {
  const authStore = useAuthStore()
  if (!authStore.isLoggedIn || !authStore.userName) return

  eventQueue.push({
    event_type: options.event,
    user_name: authStore.userName,
    module: options.module,
    action_time: new Date().toISOString(),
    detail: options.detail ? JSON.stringify(options.detail) : undefined,
    ip_address: '',
  })

  if (eventQueue.length >= 10) {
    flush()
  }
}

export const trackDirective: Directive = {
  mounted(el: HTMLElement & { _trackHandler?: (e: Event) => void }, binding: { value?: TrackOptions }) {
    const options = binding.value || {}
    const handler = () => enqueueEvent(options)
    el._trackHandler = handler
    el.addEventListener('click', handler)
  },
  unmounted(el: HTMLElement & { _trackHandler?: (e: Event) => void }) {
    if (el._trackHandler) {
      el.removeEventListener('click', el._trackHandler)
    }
  },
}

export function trackEvent(options: TrackOptions) {
  enqueueEvent(options)
}

export { flush }

export function setupTrack(app: App) {
  app.directive('track', trackDirective)

  // 页面卸载时 flush（sendBeacon 保证送达）
  window.addEventListener('beforeunload', () => flush())
  // 标签页隐藏时也 flush
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') flush()
  })
}
