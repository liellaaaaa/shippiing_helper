/**
 * 生成 UUID v4。
 *
 * 兼容非安全上下文（HTTP），因为 crypto.randomUUID() 在非 HTTPS 下不可用。
 * 使用 crypto.getRandomValues() 兜底，极老浏览器回退到 Math.random()。
 */
let _randomUUID: (() => string) | null = null

function ensureRandomUUID(): () => string {
  if (_randomUUID) return _randomUUID

  // 若 crypto.randomUUID 本身可用，直接用
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    _randomUUID = () => crypto.randomUUID()
    return _randomUUID
  }

  // 用 crypto.getRandomValues + 手动拼接（安全上下文只需要 getRandomValues）
  if (typeof crypto !== 'undefined' && typeof crypto.getRandomValues === 'function') {
    _randomUUID = () => {
      const buf = new Uint8Array(16)
      crypto.getRandomValues(buf)
      buf[6] = (buf[6] & 0x0f) | 0x40 // version 4
      buf[8] = (buf[8] & 0x3f) | 0x80 // variant
      const hex = Array.from(buf, (b) => b.toString(16).padStart(2, '0'))
      return `${hex.slice(0, 4).join('')}-${hex.slice(4, 6).join('')}-${hex.slice(6, 8).join('')}-${hex.slice(8, 10).join('')}-${hex.slice(10).join('')}`
    }
    return _randomUUID
  }

  // 最终兜底（极老浏览器）
  _randomUUID = () => {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0
      const v = c === 'x' ? r : (r & 0x3) | 0x8
      return v.toString(16)
    })
  }
  return _randomUUID
}

export function generateUuid(): string {
  return ensureRandomUUID()()
}
