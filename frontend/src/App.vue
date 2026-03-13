<template>
  <ErrorBoundary>
    <router-view v-slot="{ Component }">
      <transition name="fade-transform" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
  </ErrorBoundary>
</template>

<script setup>
import ErrorBoundary from '@/components/ErrorBoundary.vue'
</script>

<style>
/* 整个 App 级别重置与底色 */
html, body, #app {
  margin: 0;
  padding: 0;
  min-height: 100vh;
  width: 100%;
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB',
  'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  touch-action: manipulation; /* 解决 iOS 和一些移动端浏览器点击双击放大/点击延迟的问题 */
  
  /* 全局适合毛玻璃的网格渐变底色 (灰白多点渐变基调) */
  background-color: #f0f2f5;
  background-image: 
    radial-gradient(at 0% 0%, #ffffff 0px, transparent 50%),
    radial-gradient(at 100% 0%, #e9ecef 0px, transparent 50%),
    radial-gradient(at 100% 100%, #ffffff 0px, transparent 50%),
    radial-gradient(at 0% 100%, #e2e6ea 0px, transparent 50%),
    radial-gradient(at 50% 50%, #f8f9fa 0px, transparent 50%);
  background-attachment: fixed;
  transition: background-color 0.3s ease, background-image 0.3s ease;
}

body {
  margin: 0;
}

/* 极简自定义毛玻璃滚动条 */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
  background-color: transparent;
}

::-webkit-scrollbar-track {
  background-color: transparent;
}

::-webkit-scrollbar-thumb {
  background-color: rgba(0, 0, 0, 0.15);
  border-radius: 10px;
  border: 2px solid transparent;
  background-clip: padding-box;
}

::-webkit-scrollbar-thumb:hover {
  background-color: rgba(0, 0, 0, 0.25);
}

/* Route transitions */
.fade-transform-leave-active,
.fade-transform-enter-active {
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}
.fade-transform-enter-from {
  opacity: 0;
  transform: translateY(10px);
}
.fade-transform-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>
