<template>
  <el-drawer
    v-model="visible"
    :title="$t('settings.title')"
    size="420px"
    class="glass-drawer"
  >
    <el-form 
      :model="form" 
      label-position="top"
      :disabled="saving"
    >
      <el-form-item :label="$t('settings.system_name')">
        <el-input v-model="form.system_name" placeholder="metomi" />
      </el-form-item>

      <el-form-item :label="$t('settings.language')">
        <el-select 
          v-model="$i18n.locale" 
          @change="handleLangChange"
          style="width: 100%"
        >
          <el-option label="中文 (简体)" value="zh-CN" />
          <el-option label="English" value="en-US" />
        </el-select>
        <div class="form-hint">{{ $t('settings.lang_hint') }}</div>
      </el-form-item>

      <el-form-item :label="$t('settings.scraper_priority')">
        <el-select 
          v-model="form.scraper_priority" 
          multiple
          :placeholder="$t('settings.scraper_placeholder')"
          style="width: 100%"
        >
          <el-option :label="$t('common.douban')" value="Douban" />
          <el-option label="OpenLibrary" value="OpenLibrary" />
        </el-select>
      </el-form-item>

      <el-form-item :label="$t('settings.custom_code_prefix')">
        <el-input v-model="form.custom_code_prefix" placeholder="MTM-" />
      </el-form-item>

      <el-form-item :label="$t('settings.export_template')">
        <el-input 
          v-model="form.export_filename_template" 
          placeholder="{authors} - {title}" 
        />
        <div class="form-hint">{{ $t('settings.export_hint') }}</div>
      </el-form-item>

      <el-form-item :label="$t('settings.scrape_delay')">
        <el-input-number 
          v-model="form.scrape_delay_seconds" 
          :min="1" 
          :max="30" 
          controls-position="right"
        />
      </el-form-item>

      <el-form-item :label="$t('settings.view_mode_fields')">
        <el-select 
          v-model="form.view_mode_editable_fields" 
          multiple 
          :placeholder="$t('settings.view_mode_placeholder')"
          style="width: 100%"
        >
          <el-option :label="$t('settings.field_read_status')" value="read_status" />
          <el-option :label="$t('settings.field_rating')" value="rating" />
          <el-option :label="$t('settings.field_location')" value="location" />
        </el-select>
        <div class="form-hint">{{ $t('settings.view_mode_hint') }}</div>
      </el-form-item>

      <el-form-item 
        v-if="form.scraper_priority.includes('Douban')"
        :label="$t('settings.douban_cookie')"
      >
        <el-input 
          v-model="form.douban_cookie" 
          type="textarea" 
          :rows="3" 
          :placeholder="$t('settings.douban_cookie_placeholder')" 
        />
        <div class="form-hint">{{ $t('settings.douban_cookie_hint') }}<a href="/cookie-tutorial" target="_blank" style="color: #409EFF; text-decoration: none;">{{ $t('settings.douban_cookie_tutorial') }}</a></div>
      </el-form-item>

      <el-collapse v-model="activeNames" class="password-collapse">
        <el-collapse-item :title="$t('settings.change_password')" name="1">
          <div class="password-fields-wrapper">
            <el-input 
              v-model="pwdForm.old_password" 
              type="password" 
              :placeholder="$t('settings.current_password')" 
              show-password
              size="small"
              class="mb-2"
            />
            <el-input 
              v-model="pwdForm.new_password" 
              type="password" 
              :placeholder="$t('settings.new_password')" 
              show-password
              size="small"
              class="mb-2"
            />
            <el-input 
              v-model="pwdForm.confirm_password" 
              type="password" 
              :placeholder="$t('settings.confirm_password')" 
              show-password
              size="small"
            />
            <div class="pwd-action">
              <el-button 
                type="danger" 
                size="small" 
                :disabled="!pwdForm.old_password || !pwdForm.new_password || !pwdForm.confirm_password"
                :loading="pwdSaving"
                @click="handlePasswordChange"
              >
                {{ $t('settings.submit_password') }}
              </el-button>
            </div>
          </div>
        </el-collapse-item>
      </el-collapse>
    </el-form>

    <template #footer>
      <el-button @click="visible = false">{{ $t('settings.cancel') }}</el-button>
      <el-button type="primary" :loading="saving" @click="handleSave">
        {{ $t('settings.save') }}
      </el-button>
    </template>
  </el-drawer>
</template>

<script setup>
import { ref, computed, watch, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/utils/request'
import { useUserStore } from '@/store/user'
import { useSettingsStore } from '@/store/settings'

const { t } = useI18n()
const userStore = useUserStore()
const settingsStore = useSettingsStore()
const router = useRouter()

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'system-name-changed'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const saving = ref(false)

const handleLangChange = (lang) => {
  localStorage.setItem('metomi-lang', lang)
  ElMessage.success(t('settings.lang_saved'))
}

// 表单数据
const form = ref({
  system_name: 'Metomi',
  view_mode_editable_fields: ['read_status'],
  scraper_priority: ['Douban', 'OpenLibrary'],
  custom_code_prefix: 'MTM-',
  export_filename_template: '{authors} - {title} ({year})',
  scrape_delay_seconds: 3,
  douban_cookie: '',
})

const pwdSaving = ref(false)
const activeNames = ref([])
const pwdForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

// 打开时加载当前设置
watch(visible, async (newVal) => {
  if (newVal) {
    try {
      const settingsObj = await settingsStore.fetchSettings()
      for (const [sKey, sValue] of Object.entries(settingsObj)) {
        if (sKey in form.value) {
          // 数字类型需转换
          if (sKey === 'scrape_delay_seconds') {
            form.value[sKey] = parseInt(sValue) || 3
          } else if (sKey === 'scraper_priority' || sKey === 'view_mode_editable_fields') {
            try {
              form.value[sKey] = JSON.parse(sValue)
            } catch {
              form.value[sKey] = []
            }
          } else {
            form.value[sKey] = sValue
          }
        }
      }
    } catch (e) {
      // 使用默认值
    }
  }
})

const handleSave = async () => {
  saving.value = true
  try {
    // 构造批量更新 payload
    const settings = Object.entries(form.value).map(([key, value]) => {
      // eslint-disable-next-line no-useless-assignment
      let finalVal = ''
      if (Array.isArray(value)) {
        finalVal = JSON.stringify(value)
      } else {
        finalVal = String(value)
      }
      return {
        setting_key: key,
        setting_value: finalVal,
      }
    })

    await request.put('/settings', { settings })
    
    // 强制刷新本地缓存
    await settingsStore.fetchSettings(true)

    ElMessage.success(t('settings.saved'))

    // 通知父组件刷新 Logo
    emit('system-name-changed', form.value.system_name)
    
    visible.value = false
  } catch (e) {
    // request.js 已处理
  } finally {
    saving.value = false
  }
}

const handlePasswordChange = async () => {
  if (pwdForm.new_password.length < 6) {
    ElMessage.error(t('settings.pwd_too_short'))
    return
  }
  if (!/[A-Z]/.test(pwdForm.new_password) || !/[a-z]/.test(pwdForm.new_password) || !/\d/.test(pwdForm.new_password)) {
    ElMessage.error(t('settings.pwd_rule'))
    return
  }
  if (pwdForm.new_password !== pwdForm.confirm_password) {
    ElMessage.error(t('settings.pwd_mismatch'))
    return
  }

  try {
    await ElMessageBox.confirm(t('settings.pwd_confirm_msg'), t('settings.pwd_confirm_title'), {
      type: 'warning'
    })
  } catch {
    return
  }

  pwdSaving.value = true
  try {
    await request.put('/password', {
      old_password: pwdForm.old_password,
      new_password: pwdForm.new_password
    })
    
    ElMessage.success(t('settings.pwd_success'))
    userStore.logout()
    router.push('/login')
  } catch (e) {
    // request 已内部拦截处理
  } finally {
    pwdSaving.value = false
    pwdForm.old_password = ''
    pwdForm.new_password = ''
    pwdForm.confirm_password = ''
  }
}
</script>

<style scoped>
.mb-2 {
  margin-bottom: 8px;
}
.password-collapse {
  margin-top: 16px;
  background: transparent;
  border-top: none !important;
  border-bottom: none !important;
}
.password-collapse :deep(.el-collapse-item) {
  border-bottom: none !important;
}
.password-collapse :deep(.el-collapse-item__header) {
  background: transparent;
  font-weight: 600;
  color: #1a1a1a;
  border-bottom: none !important;
  box-shadow: none !important;
}
.password-collapse :deep(.el-collapse-item__wrap) {
  background: transparent;
  border-bottom: none !important;
}
.password-collapse :deep(.el-collapse-item__content) {
  border: none !important;
  background: transparent;
}
.password-fields-wrapper {
  padding: 16px 4px 8px 4px;
}
.pwd-action {
  margin-top: 12px;
  text-align: right;
}
.form-hint {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  line-height: 1.4;
}

/* Glassmorphism Drawer Overrides */
:global(.glass-drawer) {
  background: rgba(255, 255, 255, 0.65) !important;
  backdrop-filter: blur(24px) !important;
  -webkit-backdrop-filter: blur(24px) !important;
  border-left: 1px solid rgba(255, 255, 255, 0.7) !important;
  box-shadow: -8px 0 32px rgba(0, 0, 0, 0.05) !important;
}

:global(.glass-drawer .el-drawer__header) {
  margin-bottom: 0;
  padding-bottom: 20px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  color: #1a1a1a;
  font-weight: 700;
}

:global(.glass-drawer .el-drawer__body) {
  padding-top: 24px;
}

:global(.glass-drawer .el-drawer__footer) {
  background: transparent !important;
  border-top: none !important;
  box-shadow: none !important;
  padding: 20px;
}

/* Form input consistency inside glass container */
:global(.glass-drawer .el-input__wrapper),
:global(.glass-drawer .el-textarea__inner),
:global(.glass-drawer .el-select__wrapper) {
  background-color: rgba(255, 255, 255, 0.5) !important;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.02) !important;
  border: 1px solid rgba(255, 255, 255, 0.6) !important;
  border-radius: 10px !important;
  transition: all 0.3s ease;
}

:global(.glass-drawer .el-input__wrapper.is-focus),
:global(.glass-drawer .el-textarea__inner:focus),
:global(.glass-drawer .el-select__wrapper.is-focused) {
  background-color: #ffffff !important;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05), 0 0 0 1px var(--el-color-primary) inset !important;
}

:global(.glass-drawer .el-select__wrapper:hover),
:global(.glass-drawer .el-input__wrapper:hover),
:global(.glass-drawer .el-textarea__inner:hover) {
  background-color: rgba(255, 255, 255, 0.75) !important;
}

:global(.glass-drawer .el-form-item__label) {
  font-weight: 600;
  color: #2c3e50;
}
</style>
