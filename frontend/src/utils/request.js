import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'
import i18n from '@/i18n'

// 创建 axios 实例
const request = axios.create({
    baseURL: '/api/v1',
    timeout: 30000,
    withCredentials: true
})

// 请求拦截器
request.interceptors.request.use(
    config => {
        return config
    },
    error => {
        return Promise.reject(error)
    }
)

// 响应拦截器
request.interceptors.response.use(
    response => {
        return response.data
    },
    error => {
        if (error.response) {
            const status = error.response.status

            if (status === 401) {
                // 未鉴权，跳转登录（利用浏览器自带的 session cookie 失效或后端 401 触发）

                // 确保跳过不需要拦截的请求
                if (error.config.headers['X-Skip-Auth-Interceptor']) {
                    return Promise.reject(error)
                }

                // 确保不要无限跳转如果是同一页面
                if (router.currentRoute.value.path !== '/login') {
                    ElMessage.error(i18n.global.t('api.login_expired'))
                    router.push('/login')
                } else if (!error.config?.hideErrorMsg) {
                    // Fix 25: 登录失败无反馈。如果在登录页遇到 401，显示后端错误提示
                    const detail = error.response.data?.detail || i18n.global.t('api.login_expired')
                    ElMessage.error(typeof detail === 'string' ? detail : JSON.stringify(detail))
                }
            } else if (status === 403) {
                const detail = error.response.data?.detail
                // 检测到后端明确需要初始化
                if (detail && typeof detail === 'string' && detail.includes('not_initialized')) {
                    if (router.currentRoute.value.path !== '/init') {
                        router.push('/init')
                    }
                } else if (!error.config?.hideErrorMsg) {
                    ElMessage.error(typeof detail === 'string' ? detail : i18n.global.t('api.no_permission'))
                }
            } else if (!error.config?.hideErrorMsg) {
                // 其他错误统一提示后端的 detail 或通用报错
                const detail = error.response.data?.detail || i18n.global.t('api.request_failed')
                ElMessage.error(typeof detail === 'string' ? detail : JSON.stringify(detail))
            }
        } else if (!error.config?.hideErrorMsg) {
            ElMessage.error(i18n.global.t('api.network_error'))
        }

        return Promise.reject(error)
    }
)

export default request
