import { createApp } from 'vue'
import { createPinia } from 'pinia'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import { ElInfiniteScroll } from 'element-plus'

import App from './App.vue'

// ────────────────────────────────────────────────────────────────
// macOS Edge 焦点抢占修复
// vue-router 会在 visibilitychange/pagehide 时调用 history.replaceState
// 保存滚动位置。在 macOS Edge 上，这会导致浏览器抢占焦点并切换 Space。
//
// 解决方案（三重防护）：
// 1. 阻止 vue-router 收到 visibilitychange (hidden) / pagehide 事件
// 2. 阻止 history.replaceState/pushState 在页面隐藏时执行
// 3. 必须在 import router 之前安装，否则 vue-router 会先注册监听器
// ────────────────────────────────────────────────────────────────
;(() => {
    // 1) 拦截 visibilitychange：当页面变 hidden 时阻止事件继续传播
    //    vue-router 也注册在 document 上，但我们先注册，stopImmediatePropagation
    //    会阻止同一元素上后续的监听器执行
    document.addEventListener('visibilitychange', (e) => {
        if (document.visibilityState === 'hidden') {
            e.stopImmediatePropagation()
        }
    }, true)

    // 2) 拦截 pagehide（vue-router 注册在 window 上）
    window.addEventListener('pagehide', (e) => {
        e.stopImmediatePropagation()
    }, true)

    // 3) 兜底：即使事件泄漏，也阻止 history API 在后台执行
    const rawReplaceState = history.replaceState.bind(history)
    history.replaceState = (...args) => {
        if (document.visibilityState === 'hidden' || !document.hasFocus()) return
        return rawReplaceState(...args)
    }

    const rawPushState = history.pushState.bind(history)
    history.pushState = (...args) => {
        if (document.visibilityState === 'hidden' || !document.hasFocus()) return
        return rawPushState(...args)
    }
})()

import './assets/main.css'
import './assets/book-modal.css'
import router from './router'
import i18n from './i18n'
import request from './utils/request'
import { useAppStore } from '@/store/app'
import { useUserStore } from '@/store/user'

const initApp = async () => {
    const pinia = createPinia()
    const app = createApp(App)

    for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
        app.component(key, component)
    }

    app.use(ElInfiniteScroll)
    app.use(pinia)

    // 全局错误处理
    app.config.errorHandler = (err, vm, info) => {
        console.error('全局捕获的错误:', err, info)
        // 尝试获取全局挂载的 ElMessage
        const elMsg = (vm && vm.$message) || window.ElMessage
        if (typeof elMsg === 'function') {
            elMsg({
                type: 'error',
                message: `由于网络或未知错误导致应用异常，请刷新重试 (${info})`
            })
        }
    }

    // 在挂载前获取初始化状态
    const appStore = useAppStore()
    const userStore = useUserStore()

    try {
        const res = await request.get('/init/status', {
            headers: { 'X-Skip-Auth-Interceptor': 'true' }
        })
        appStore.setInitialized(res.is_initialized)

        // Fix 28 (Session Hydration): 如果系统已初始化，尝试静默恢复会话
        if (res.is_initialized) {
            await userStore.initSession()
        }
    } catch (error) {
        console.error('Failed to get init status:', error)
        appStore.setInitialized(false)
    }

    app.use(router)
    app.use(i18n)

    app.mount('#app')
}

initApp()
