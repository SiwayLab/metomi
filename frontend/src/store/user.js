import { defineStore } from 'pinia'
import { ref } from 'vue'
import request from '@/utils/request'
import router from '@/router'
import { ElMessage } from 'element-plus'

export const useUserStore = defineStore('user', () => {
    const userInfo = ref(null)

    // 登录动作
    const login = async (username, password) => {
        try {
            // 后端 OAuth2 PasswordBearer 使用 FormData
            const formData = new URLSearchParams()
            formData.append('username', username)
            formData.append('password', password)

            // axios request 会拦截响应并返回 response.data
            const res = await request.post('/login', formData, {
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            })

            // 登录成功后获取用户信息
            await getUserInfo()

            import('@/i18n').then((module) => {
                ElMessage.success(module.default.global.t('api.login_success'))
            })
            router.push('/')
            return true
        } catch (error) {
            // 错误已在 request.js 拦截器中提示
            return false
        }
    }

    // 获取当前用户信息
    const getUserInfo = async () => {
        try {
            const res = await request.get('/me')
            userInfo.value = res
            return res
        } catch (error) {
            console.error('获取用户信息失败', error)
            return null
        }
    }

    // 页面刷新时的静默会话恢复
    const initSession = async () => {
        try {
            const res = await request.get('/me', {
                headers: { 'X-Skip-Auth-Interceptor': 'true' }
            })
            userInfo.value = res
            return true
        } catch (error) {
            userInfo.value = null
            return false
        }
    }

    // 登出动作
    const logout = async () => {
        try {
            await request.post('/logout')
        } catch (e) {
            console.error('Logout error:', e)
        }
        userInfo.value = null
        router.push('/login')
    }

    return {
        userInfo,
        login,
        getUserInfo,
        initSession,
        logout
    }
})
