import { createRouter, createWebHistory } from 'vue-router'
import { useAppStore } from '@/store/app'
import { useUserStore } from '@/store/user'

const routes = [
    {
        path: '/init',
        name: 'Init',
        component: () => import('@/views/Init.vue'),
        meta: {
            title: '初始化设置 - Metomi',
            noAuth: true
        }
    },
    {
        path: '/cookie-tutorial',
        name: 'CookieTutorial',
        component: () => import('@/views/CookieTutorial.vue'),
        meta: {
            title: '如何获取豆瓣 Cookie - Metomi',
            noAuth: true
        }
    },
    {
        path: '/login',
        name: 'Login',
        component: () => import('@/views/Login.vue'),
        meta: {
            title: '登录 - Metomi',
            noAuth: true
        }
    },
    {
        path: '/',
        name: 'Home',
        component: () => import('@/views/Home.vue'),
        meta: {
            title: '首页 - Metomi'
        }
    },
    {
        path: '/reader/:book_id/:file_id/:format',
        name: 'Reader',
        component: () => import('@/views/Reader.vue'),
        meta: {
            title: '阅读 - Metomi'
        }
    }
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

// 全局前置守卫
router.beforeEach((to, from, next) => {
    // 设置页面标题
    if (to.meta.title) {
        document.title = to.meta.title
    }

    const appStore = useAppStore()
    const isInit = appStore.isInitialized

    // 1. 如果系统尚未初始化：
    if (isInit === false) {
        if (to.path !== '/init' && to.path !== '/cookie-tutorial') {
            return next('/init')
        }
        return next() // 允许访问 /init 和 /cookie-tutorial
    }

    // 2. 如果系统已初始化：
    if (isInit === true) {
        if (to.path === '/init') {
            return next('/login')
        }
    }

    // --- 常规授权逻辑 ---
    // 这里简单依赖 userInfo（或者由后端拦截器返回 401 自动处理）
    const userStore = useUserStore()
    const isLoggedIn = !!userStore.userInfo?.username

    // 如果去登录页，且已登录，直接跳转首页
    if (to.path === '/login' && isLoggedIn) {
        return next('/')
    }

    // 如果访问需要授权的页面，且无鉴权标志
    if (!to.meta.noAuth && !isLoggedIn) {
        return next('/login')
    }

    // 其他情况放行
    next()
})

export default router
