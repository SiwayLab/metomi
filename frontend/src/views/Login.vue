<template>
  <div class="login-wrapper">
    <el-card class="login-card" shadow="hover">
      <div class="login-header">
        <h1 class="logo-text">Metomi</h1>
      </div>
      
      <el-form 
        :model="form" 
        :rules="rules" 
        ref="formRef"
        @keyup.enter="handleLogin"
      >
        <el-form-item prop="username">
          <el-input 
            v-model="form.username" 
            :placeholder="$t('login.username_placeholder')" 
            size="large"
            :prefix-icon="User"
          />
        </el-form-item>
        
        <el-form-item prop="password">
          <el-input 
            v-model="form.password" 
            :placeholder="$t('login.password_placeholder')" 
            type="password" 
            size="large"
            show-password
            :prefix-icon="Lock"
          />
        </el-form-item>
        
        <el-form-item class="submit-btn-item">
          <el-button 
            type="primary" 
            size="large" 
            class="submit-btn" 
            :loading="loading"
            @click="handleLogin"
          >
            {{ $t('login.submit') }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { User, Lock } from '@element-plus/icons-vue'
import { useUserStore } from '@/store/user'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const userStore = useUserStore()
const formRef = ref(null)
const loading = ref(false)

const form = reactive({
  username: '',
  password: ''
})

const rules = reactive({
  username: [
    { required: true, message: t('login.username_placeholder'), trigger: 'blur' }
  ],
  password: [
    { required: true, message: t('login.password_placeholder'), trigger: 'blur' }
  ]
})

const handleLogin = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        await userStore.login(form.username, form.password)
      } finally {
        loading.value = false
      }
    }
  })
}
</script>

<style scoped>
.login-wrapper {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: transparent;
  position: relative;
  overflow: hidden;
}

.login-card {
  width: 400px;
  max-width: 90vw;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.5);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08) !important;
  z-index: 10;
  background: rgba(255, 255, 255, 0.65);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
  margin-top: 10px;
}

.logo-text {
  font-size: 32px;
  font-weight: 800;
  color: #1a1a1a;
  margin: 0 0 8px 0;
  letter-spacing: -0.5px;
}

.submit-btn-item {
  margin-top: 32px;
  margin-bottom: 10px;
}

.submit-btn {
  width: 100%;
  font-size: 16px;
  letter-spacing: 2px;
  border-radius: 4px;
  font-weight: 600;
}
</style>
