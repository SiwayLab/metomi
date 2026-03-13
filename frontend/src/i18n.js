import { createI18n } from 'vue-i18n'
import zhCN from './locales/zh-CN'
import enUS from './locales/en-US'

// 获取浏览器语言
const navLang = navigator.language || navigator.userLanguage
const localLang = localStorage.getItem('metomi-lang')

let defaultLang = 'zh-CN'

if (localLang) {
    defaultLang = localLang
} else if (navLang) {
    // 如果浏览器语言包含 zh，则默认中文；否则强制降级为英文
    if (navLang.toLowerCase().includes('zh')) {
        defaultLang = 'zh-CN'
    } else {
        defaultLang = 'en-US'
    }
    localStorage.setItem('metomi-lang', defaultLang)
}

const i18n = createI18n({
    legacy: false, // 启用 Composition API 模式
    locale: defaultLang,
    fallbackLocale: 'en-US',
    messages: {
        'zh-CN': zhCN,
        'en-US': enUS
    }
})

export default i18n
