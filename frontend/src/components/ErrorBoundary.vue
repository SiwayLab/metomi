<template>
  <div v-if="hasError" class="error-boundary">
    <div class="error-content">
      <el-icon class="error-icon" :size="48"><WarningFilled /></el-icon>
      <h2>页面加载出错</h2>
      <p>抱歉，应用在渲染时遇到了意外的错误。</p>
      
      <div v-if="errorInfo" class="error-details">
        <div class="error-message">{{ errorInfo.message }}</div>
        <div class="error-where">{{ errorInfo.where }}</div>
      </div>

      <el-button type="primary" @click="reloadPage" class="reload-btn">
        <el-icon><Refresh /></el-icon>
        重新加载页面
      </el-button>
    </div>
  </div>
  <slot v-else></slot>
</template>

<script setup>
import { ref, onErrorCaptured } from 'vue'
import { WarningFilled, Refresh } from '@element-plus/icons-vue'

const hasError = ref(false)
const errorInfo = ref(null)

onErrorCaptured((err, instance, info) => {
  console.error('[ErrorBoundary Captured]', err, info)
  hasError.value = true
  errorInfo.value = {
    message: err.message || String(err),
    where: info
  }
  // 返回 false 阻止错误继续向上传递到控制台 Uncaught 
  return false
})

const reloadPage = () => {
  window.location.reload()
}
</script>

<style scoped>
.error-boundary {
  height: 100vh;
  width: 100vw;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: #f5f7fa;
}

.error-content {
  background: white;
  padding: 40px;
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.1);
  text-align: center;
  max-width: 500px;
}

.error-icon {
  color: #f56c6c;
  margin-bottom: 16px;
}

h2 {
  margin: 0 0 12px;
  color: #303133;
}

p {
  color: #606266;
  margin: 0 0 24px;
}

.error-details {
  background: #fef0f0;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 24px;
  text-align: left;
  border: 1px solid #fde2e2;
  overflow: auto;
  max-height: 200px;
}

.error-message {
  color: #f56c6c;
  font-family: monospace;
  font-weight: bold;
  margin-bottom: 8px;
  word-break: break-all;
}

.error-where {
  color: #909399;
  font-size: 13px;
  font-family: monospace;
}

.reload-btn {
  width: 100%;
}
</style>
