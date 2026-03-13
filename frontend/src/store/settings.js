import { defineStore } from 'pinia'
import { ref } from 'vue'
import request from '@/utils/request'

export const useSettingsStore = defineStore('settings', () => {
    const settings = ref({})
    const isFetching = ref(false)
    const hasFetched = ref(false)

    const fetchSettings = async (force = false) => {
        if (!force && hasFetched.value) return settings.value

        if (isFetching.value) {
            // Wait for the ongoing request
            return new Promise((resolve) => {
                const check = setInterval(() => {
                    if (!isFetching.value) {
                        clearInterval(check)
                        resolve(settings.value)
                    }
                }, 50)
            })
        }

        isFetching.value = true
        try {
            const data = await request.get('/settings')
            // data is an array of { setting_key, setting_value }
            const mappedSettings = {}
            if (Array.isArray(data)) {
                data.forEach(item => {
                    mappedSettings[item.setting_key] = item.setting_value
                })
            }
            settings.value = mappedSettings
            hasFetched.value = true
            return settings.value
        } catch (error) {
            console.error('Failed to fetch settings:', error)
            return {}
        } finally {
            isFetching.value = false
        }
    }

    const getSetting = (key, defaultVal = null) => {
        return settings.value[key] !== undefined ? settings.value[key] : defaultVal
    }

    // 更新特定的设置
    const updateSettingLocally = (key, value) => {
        settings.value[key] = value
    }

    return {
        settings,
        fetchSettings,
        getSetting,
        updateSettingLocally,
        hasFetched
    }
})
