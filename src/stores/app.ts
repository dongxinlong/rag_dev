import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  /** 侧边栏是否折叠 */
  const sidebarCollapsed = ref(false)
  /** 设备类型 */
  const device = ref<'desktop' | 'mobile'>('desktop')
  /** 全局尺寸 */
  const size = ref<'small' | 'default' | 'large'>('default')

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function setDevice(val: 'desktop' | 'mobile') {
    device.value = val
  }

  function setSize(val: 'small' | 'default' | 'large') {
    size.value = val
  }

  return {
    sidebarCollapsed,
    device,
    size,
    toggleSidebar,
    setDevice,
    setSize,
  }
})
