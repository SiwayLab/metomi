import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
    // 默认视图模式：'view' 模式下隐藏破坏性或管理级操作按钮
    // 'edit' 模式下显示导入图书、删除等高级管理功能
    const initMode = localStorage.getItem('metomi_ui_mode') || 'view'
    const uiMode = ref(initMode)

    const toggleMode = () => {
        uiMode.value = uiMode.value === 'view' ? 'edit' : 'view'
        localStorage.setItem('metomi_ui_mode', uiMode.value)
    }

    const setMode = (mode) => {
        if (mode === 'view' || mode === 'edit') {
            uiMode.value = mode
            localStorage.setItem('metomi_ui_mode', uiMode.value)
        }
    }

    const isInitialized = ref(null)

    const setInitialized = (val) => {
        isInitialized.value = val
    }

    return {
        uiMode,
        isInitialized,
        toggleMode,
        setMode,
        setInitialized
    }
})
