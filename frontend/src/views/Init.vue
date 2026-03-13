<template>
  <div class="init-wrapper">
    <!-- 全屏撒花特效容器 -->
    <div v-if="showConfetti" class="confetti-container">
      <div v-for="i in 50" :key="i" class="confetti-piece"></div>
    </div>

    <el-card class="init-card" shadow="always">
      <div class="init-header">
        <h1 class="logo-text">{{ $t('init.title') }}</h1>
        <p class="subtitle">{{ $t('init.subtitle') }}</p>
      </div>

      <el-steps :active="activeStep" finish-status="success" align-center class="init-steps">
        <el-step :title="$t('init.step_language')" />
        <el-step :title="$t('init.step_security')" />
        <el-step :title="$t('init.step_scraper')" />
        <el-step :title="$t('init.step_preference')" />
      </el-steps>

      <el-form 
        :model="form" 
        :rules="rules" 
        ref="formRef"
        label-position="top"
        class="init-form"
      >
        <!-- Step 1: 语言偏好 -->
        <div v-show="activeStep === 0" class="step-content flex-center">
          <div class="language-box">
            <div class="lang-label">{{ $t('init.step_language') }}</div>
            <el-select 
              v-model="$i18n.locale" 
              size="large" 
              class="lang-select"
              @change="handleSetLanguage"
            >
              <el-option label="中文 (简体)" value="zh-CN">
                <span style="float: left">中文 (简体)</span>
                <span style="float: right; color: var(--el-text-color-secondary); font-size: 13px;">zh-CN</span>
              </el-option>
              <el-option label="English" value="en-US">
                <span style="float: left">English</span>
                <span style="float: right; color: var(--el-text-color-secondary); font-size: 13px;">en-US</span>
              </el-option>
            </el-select>
          </div>
        </div>

        <!-- Step 2: 核心安全 -->
        <div v-show="activeStep === 1" class="step-content">
          <el-form-item :label="$t('init.username')" prop="username">
            <el-input 
              v-model="form.username" 
              :placeholder="$t('init.username_placeholder')" 
              size="large"
            />
          </el-form-item>
          
          <el-form-item :label="$t('init.password')" prop="password">
            <el-input 
              v-model="form.password" 
              :placeholder="$t('init.password_placeholder')" 
              type="password" 
              size="large"
              show-password
            />
          </el-form-item>

          <el-form-item :label="$t('init.confirm_password')" prop="confirm_password">
            <el-input 
              v-model="form.confirm_password" 
              :placeholder="$t('init.confirm_password_placeholder')" 
              type="password" 
              size="large"
              show-password
            />
          </el-form-item>
        </div>

        <!-- Step 3: 数据抓取与刮削 -->
        <div v-show="activeStep === 2" class="step-content">
          <el-form-item :label="$t('init.scraper_priority')" prop="settings.scraper_priority">
            <el-select 
              v-model="form.settings.scraper_priority" 
              multiple 
              size="large"
              style="width: 100%"
            >
              <el-option 
                v-for="source in availableScraperSources" 
                :key="source.value" 
                :label="source.label" 
                :value="source.value" 
              />
            </el-select>
          </el-form-item>

          <el-form-item :label="$t('init.scrape_delay')" prop="settings.scrape_delay_seconds">
            <el-input-number 
              v-model="form.settings.scrape_delay_seconds" 
              :min="1" 
              :max="30" 
              size="large"
            />
            <div class="form-tip">{{ $t('init.scrape_delay_tip') }}</div>
          </el-form-item>

          <el-form-item :label="$t('init.custom_code_prefix')" prop="settings.custom_code_prefix">
            <el-input 
              v-model="form.settings.custom_code_prefix" 
              size="large"
            />
          </el-form-item>

          <el-form-item 
            v-if="form.settings.scraper_priority.includes('Douban')"
            prop="settings.douban_cookie"
          >
            <template #label>
              {{ $t('init.douban_cookie') }}
              <router-link to="/cookie-tutorial" target="_blank" class="tutorial-link">{{ $t('init.douban_cookie_tutorial') }}</router-link>
            </template>
            <el-input 
              v-model="form.settings.douban_cookie" 
              type="textarea"
              :rows="3"
              :placeholder="$t('init.douban_cookie_placeholder')"
            />
            <div class="form-tip">{{ $t('init.douban_cookie_tip') }}</div>
          </el-form-item>
        </div>

        <!-- Step 4: 偏好与界面配置 -->
        <div v-show="activeStep === 3" class="step-content">
          <el-form-item :label="$t('init.system_name')" prop="settings.system_name">
            <el-input 
              v-model="form.settings.system_name" 
              :placeholder="$t('init.system_name_placeholder')" 
              size="large"
            />
          </el-form-item>

          <el-form-item :label="$t('init.view_mode_editable_fields')" prop="settings.view_mode_editable_fields">
            <el-select 
              v-model="form.settings.view_mode_editable_fields" 
              multiple 
              size="large"
              style="width: 100%"
            >
              <el-option :label="$t('init.field_read_status')" value="read_status" />
              <el-option :label="$t('init.field_rating')" value="rating" />
              <el-option :label="$t('init.field_location')" value="location" />
            </el-select>
            <div class="form-tip">{{ $t('init.view_mode_editable_fields_tip') }}</div>
          </el-form-item>

          <el-form-item :label="$t('init.export_filename_template')" prop="settings.export_filename_template">
            <el-input 
              v-model="form.settings.export_filename_template" 
              size="large"
            />
            <div class="form-tip template-vars">
              <span>{{ $t('init.export_filename_template_tip') }}</span>
              <div class="var-list">
                <span class="var-item"><el-tag size="small" type="info">{title}</el-tag> {{ $t('init.var_title') }}</span>
                <span class="var-item"><el-tag size="small" type="info">{authors}</el-tag> {{ $t('init.var_authors') }}</span>
                <span class="var-item"><el-tag size="small" type="info">{year}</el-tag> {{ $t('init.var_year') }}</span>
                <span class="var-item"><el-tag size="small" type="info">{publisher}</el-tag> {{ $t('init.var_publisher') }}</span>
                <span class="var-item"><el-tag size="small" type="info">{isbn}</el-tag> {{ $t('init.var_isbn') }}</span>
                <span class="var-item" v-if="$i18n.locale !== 'en-US'"><el-tag size="small" type="info">{douban_id}</el-tag> {{ $t('init.var_douban_id') }}</span>
                <span class="var-item"><el-tag size="small" type="info">{custom_code}</el-tag> {{ $t('init.var_custom_code') }}</span>
              </div>
            </div>
          </el-form-item>
        </div>

        <!-- 底部操作按钮 -->
        <div class="init-actions">
          <el-button 
            v-if="activeStep > 0" 
            size="large" 
            @click="prevStep"
          >
            {{ $t('init.prev_step') }}
          </el-button>
          
          <el-button 
            v-if="activeStep < 3" 
            type="primary" 
            size="large" 
            @click="nextStep"
          >
            {{ $t('init.next_step') }}
          </el-button>
          
          <el-button 
            v-if="activeStep === 3" 
            type="success" 
            size="large" 
            :loading="loading"
            class="submit-btn"
            @click="handleInit"
          >
            {{ $t('init.finish_init') }}
          </el-button>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'
import request from '@/utils/request'

const router = useRouter()
const { t, locale } = useI18n()
const formRef = ref(null)
const activeStep = ref(0)
const loading = ref(false)
const showConfetti = ref(false)

const form = reactive({
  username: '',
  password: '',
  confirm_password: '',
  settings: {
    system_name: 'Metomi',
    view_mode_editable_fields: ['read_status'],
    export_filename_template: '{authors} - {title} ({year})',
    scraper_priority: ['Douban', 'OpenLibrary'],
    scrape_delay_seconds: 3,
    custom_code_prefix: 'MTM-',
    douban_cookie: ''
  }
})

// 改变语言时，保存到本地，并确保默认选中的过滤源被移出
const handleSetLanguage = (lang) => {
  locale.value = lang
  localStorage.setItem('metomi-lang', lang)
}

// 智能屏蔽 Douban 源：如果是英文环境，不在候选列表提供
const availableScraperSources = computed(() => {
  if (locale.value === 'en-US') {
    return [{ label: 'OpenLibrary', value: 'OpenLibrary' }]
  }
  return [
    { label: t('common.douban'), value: 'Douban' },
    { label: 'OpenLibrary', value: 'OpenLibrary' }
  ]
})

// 监听语言变化，如果当前是 en-US 并且选择了 Douban，就把它移出
watch(locale, (newLang) => {
  if (newLang === 'en-US') {
    form.settings.scraper_priority = form.settings.scraper_priority.filter(s => s !== 'Douban')
  } else {
    // 切换回中文如果原先没有 Douban，可选择加回来
    if (!form.settings.scraper_priority.includes('Douban')) {
      form.settings.scraper_priority.unshift('Douban')
    }
  }
})

const validateConfirmPassword = (rule, value, callback) => {
  if (value === '') {
    callback(new Error(t('init.confirm_password_placeholder')))
  } else if (value !== form.password) {
    callback(new Error(t('init.password_mismatch')))
  } else {
    callback()
  }
}

// 共享密码强度校验函数
const validatePasswordStrength = (rule, value, callback) => {
  if (!value) {
    callback(new Error(t('init.password_required')))
  } else if (value.length < 6) {
    callback(new Error(t('settings.pwd_too_short')))
  } else if (!/[A-Z]/.test(value) || !/[a-z]/.test(value) || !/\d/.test(value)) {
    callback(new Error(t('settings.pwd_rule')))
  } else {
    callback()
  }
}

// rules 需要响应式（或方法返回）以跟顺语言切换
const rules = computed(() => {
  return {
    username: [
      { required: true, message: t('init.username_required'), trigger: 'blur' },
      { min: 3, max: 20, message: 'Length should be 3 to 20', trigger: 'blur' }
    ],
    password: [
      { required: true, message: t('init.password_required'), trigger: 'blur' },
      { validator: validatePasswordStrength, trigger: 'blur' }
    ],
    confirm_password: [
      { validator: validateConfirmPassword, trigger: 'blur' }
    ],
    'settings.system_name': [
      { required: true, message: t('init.system_name_required'), trigger: 'blur' }
    ]
  }
})

const nextStep = async () => {
  if (!formRef.value) return
  
  // 只验证当前步骤的字段
  let fieldsToValidate = []
  if (activeStep.value === 1) { // 旧的步骤 0
    fieldsToValidate = ['username', 'password', 'confirm_password']
  } else if (activeStep.value === 3) { // 旧的步骤 2
    fieldsToValidate = ['settings.system_name']
  }
  
  if (fieldsToValidate.length > 0) {
    try {
      await formRef.value.validateField(fieldsToValidate)
      activeStep.value++
    } catch (e) {
      // 验证失败，不进入下一步
    }
  } else {
    if (activeStep.value === 0) {
      // 清除因切换语言（导致 rules 重新计算）而自动触发的整表单校验报红
      formRef.value.clearValidate()
    }
    activeStep.value++
  }
}

const prevStep = () => {
  activeStep.value--
}

const handleInit = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      
      try {
        // 转换 settings 格式为后端需要的 list[SystemSettingUpdate]
        const settingsList = Object.keys(form.settings).map(key => {
          let value = form.settings[key]
          // 处理数组格式
          if (Array.isArray(value)) {
            value = JSON.stringify(value)
          } else {
            value = String(value)
          }
          return { setting_key: key, setting_value: value }
        })

        const payload = {
          username: form.username,
          password: form.password,
          language: locale.value, // <--- 关键修改：提交语言
          settings: settingsList
        }

        await request.post('/init/setup', payload)
        
        // 成功特效
        showConfetti.value = true
        ElMessage({
          message: t('init.success_msg'),
          type: 'success',
          duration: 3000,
          customClass: 'celebration-message'
        })
        
        setTimeout(() => {
          // 强制刷新页面跳往登录，以清空路由中的 isInitializedCache 内存缓存
          window.location.href = '/login'
        }, 1500)
        
      } catch (error) {
        // 错误已由 request 拦截器处理
        console.error('Init failed:', error)
      } finally {
        loading.value = false
      }
    }
  })
}
</script>

<style scoped>
.init-wrapper {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: transparent;
  position: relative;
}

.lang-switcher {
  position: absolute;
  top: 24px;
  right: 24px;
  z-index: 20;
}

.lang-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  padding: 8px 16px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255,255,255,0.4);
  color: #303133;
  font-weight: 500;
  transition: all 0.3s ease;
}

.lang-btn:hover {
  background: rgba(255, 255, 255, 0.9);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
}

.init-card {
  width: 600px;
  max-width: 90vw;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.5);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08) !important;
  z-index: 10;
  background: rgba(255, 255, 255, 0.65);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
}

.init-header {
  text-align: center;
  margin-bottom: 30px;
  margin-top: 10px;
}

.logo-text {
  font-size: 32px;
  font-weight: 800;
  color: #1a1a1a;
  margin: 0 0 8px 0;
  letter-spacing: -0.5px;
}

.subtitle {
  color: #606266;
  margin: 0;
  font-size: 14px;
  white-space: pre-line;
  line-height: 1.6;
}

.init-steps {
  margin-bottom: 40px;
}

.step-content {
  min-height: 280px;
  animation: fadeIn 0.3s ease-in-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.flex-center {
  display: flex;
  justify-content: center;
  align-items: center;
}

.language-box {
  text-align: center;
  padding: 40px 0;
  margin-top: -30px;
}

.lang-label {
  font-size: 18px;
  color: #303133;
  margin-bottom: 20px;
  font-weight: 600;
  letter-spacing: 1px;
}

.lang-select {
  width: 280px;
}

.init-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #ebeef5;
}

.submit-btn {
  font-weight: 600;
  letter-spacing: 1px;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  line-height: 1.4;
}

.template-vars {
  margin-top: 8px;
}

.var-list {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 16px;
  margin-top: 8px;
}

.var-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #606266;
}

.tutorial-link {
  font-size: 13px;
  color: #409EFF;
  text-decoration: none;
  margin-left: 10px;
  font-weight: normal;
}

.tutorial-link:hover {
  text-decoration: underline;
}

/* 简易全屏撒花 CSS 特效 */
.confetti-container {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  pointer-events: none;
  z-index: 9999;
}

.confetti-piece {
  position: absolute;
  width: 10px;
  height: 20px;
  background-color: #f00;
  top: -10%;
  opacity: 0;
}

@keyframes fall {
  0% { opacity: 1; top: -10%; transform: translateX(0) rotate(0deg); }
  100% { opacity: 1; top: 110%; transform: translateX(100px) rotate(360deg); }
}

.confetti-piece:nth-child(even) { background-color: #409EFF; }
.confetti-piece:nth-child(3n) { background-color: #67C23A; }
.confetti-piece:nth-child(4n) { background-color: #E6A23C; }
.confetti-piece:nth-child(5n) { background-color: #F56C6C; }

.confetti-piece:nth-child(1) { left: 10%; animation: fall 1.2s linear forwards; }
.confetti-piece:nth-child(2) { left: 20%; animation: fall 1.5s linear forwards 0.1s; }
.confetti-piece:nth-child(3) { left: 30%; animation: fall 1.1s linear forwards 0.2s; }
.confetti-piece:nth-child(4) { left: 40%; animation: fall 1.4s linear forwards; }
.confetti-piece:nth-child(5) { left: 50%; animation: fall 1.3s linear forwards 0.3s; }
.confetti-piece:nth-child(6) { left: 60%; animation: fall 1.6s linear forwards 0.1s; }
.confetti-piece:nth-child(7) { left: 70%; animation: fall 1.2s linear forwards 0.4s; }
.confetti-piece:nth-child(8) { left: 80%; animation: fall 1.5s linear forwards 0.2s; }
.confetti-piece:nth-child(9) { left: 90%; animation: fall 1.1s linear forwards; }
/* 复制更多以覆盖屏幕 */
.confetti-piece:nth-child(n+10) { 
  left: calc(10% * (n - 9)); 
  animation: fall calc(1s + 0.1s * n) linear forwards calc(0.1s * n); 
}
</style>
<style>
/* 全局覆盖消息提示的居中与字号 */
.celebration-message {
  padding: 20px 40px !important;
  font-size: 18px !important;
  font-weight: bold;
}
</style>
