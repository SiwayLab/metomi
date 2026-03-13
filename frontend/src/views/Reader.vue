<template>
  <div class="reader-container">
    <!-- 顶部控制栏 -->
    <header class="reader-toolbar">
      <div class="toolbar-left">
        <el-button text @click="goBack">
          <el-icon><ArrowLeft /></el-icon> {{ $t('reader.back_to_library') }}
        </el-button>
        <el-button text @click="tocVisible = !tocVisible" :type="tocVisible ? 'primary' : ''">
          <el-icon><Menu /></el-icon> {{ $t('reader.toc') }}
        </el-button>
      </div>
      <div class="toolbar-center">
        <!-- PDF 分页控制 -->
        <template v-if="isPdf">
          <el-button :disabled="currentPage <= 1" @click="jumpToPage(currentPage - 1)" size="small">{{ $t('reader.prev_page') }}</el-button>
          <el-input-number
            v-model="jumpPageInput"
            :min="1"
            :max="totalPages || 1"
            size="small"
            controls-position="right"
            class="page-input"
            @change="jumpToPage(jumpPageInput)"
          />
          <span class="page-indicator"> / {{ totalPages || '...' }}</span>
          <el-button :disabled="currentPage >= totalPages" @click="jumpToPage(currentPage + 1)" size="small">{{ $t('reader.next_page') }}</el-button>
        </template>
        <!-- EPUB 翻页控制 -->
        <template v-if="isEpub">
          <el-button @click="epubPrev" size="small">{{ $t('reader.prev_page') }}</el-button>
          <span class="page-indicator">{{ epubLocationLabel || $t('reader.epub_reading') }}</span>
          <el-button @click="epubNext" size="small">{{ $t('reader.next_page') }}</el-button>
        </template>
      </div>
      <div class="toolbar-right">
        <el-tag type="info" size="small">{{ formatType.toUpperCase() }}</el-tag>
      </div>
    </header>

    <div class="reader-body">
      <!-- TOC 侧边栏 -->
      <aside v-show="tocVisible" class="toc-sidebar">
        <div class="toc-header">{{ $t('reader.toc') }}</div>
        <div class="toc-list" v-if="tocItems.length">
          <div
            v-for="(item, idx) in tocItems"
            :key="idx"
            class="toc-item"
            :style="{ paddingLeft: (item.level || 0) * 16 + 12 + 'px' }"
            @click="handleTocClick(item)"
          >
            {{ item.label }}
          </div>
        </div>
        <div v-else class="toc-empty">{{ $t('reader.no_toc') }}</div>
      </aside>

      <!-- 阅读区域 -->
      <main class="reader-main" ref="readerMain">
        <!-- PDF 懒加载渲染：使用 pdfjs-dist 直接渲染到 canvas -->
        <div v-if="isPdf" class="pdf-viewer">
          <div
            v-for="page in totalPages"
            :key="page"
            :ref="el => setPdfPageRef(el, page)"
            :data-page="page"
            class="pdf-page-wrapper"
            :style="{ aspectRatio: pageAspectRatios[page] || (1 / 1.414) }"
          >
            <canvas :ref="el => setPdfCanvasRef(el, page)" class="pdf-canvas"></canvas>
          </div>
          <!-- 初始加载提示 -->
          <div v-if="totalPages === 0 && !loading" class="pdf-init-loading">
            <el-icon class="is-loading" :size="32"><Loading /></el-icon>
            <p>{{ $t('reader.parsing_pdf') }}</p>
          </div>
        </div>

        <!-- EPUB 渲染容器 + 点击翻页区域 -->
        <div v-if="isEpub" class="epub-wrapper">
          <div class="epub-click-zone epub-click-left" @click="epubPrev"></div>
          <div ref="epubContainer" class="epub-viewer"></div>
          <div class="epub-click-zone epub-click-right" @click="epubNext"></div>
        </div>

        <!-- 加载状态 -->
        <div v-if="loading" class="loading-overlay">
          <el-icon class="is-loading" :size="48"><Loading /></el-icon>
          <p>{{ $t('reader.loading_book') }}</p>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { Notebook, ArrowLeft, ArrowRight, List as ListIcon, Sunny, Moon, Back } from '@element-plus/icons-vue'
import request from '@/utils/request'
import { usePdfReader } from '@/composables/usePdfReader'
import { useEpubReader } from '@/composables/useEpubReader'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const formatType = ref('pdf')
const isPdf = computed(() => formatType.value === 'pdf')
const isEpub = computed(() => formatType.value === 'epub')
const loading = ref(true)
const tocVisible = ref(false)
const tocItems = ref([])
const isDarkMode = ref(false)

const readerMain = ref(null)
const epubContainer = ref(null)

const currentPage = ref(1)
const totalPages = ref(0)
const jumpPageInput = ref(1)
const pageAspectRatios = ref({})

let _bookId = 0
let _fileId = 0
let _format = ''
let localBlobUrl = ''
let progressTimer = null

const {
  initPdf,
  setPdfPageRef,
  setPdfCanvasRef,
  jumpToPage,
  destroyPdf
} = usePdfReader({
  readerMain,
  currentPage,
  totalPages,
  tocItems,
  loading,
  pageAspectRatios,
  t
})

const {
  epubLocationLabel,
  initEpub,
  epubPrev,
  epubNext,
  jumpToEpubHref,
  getEpubCfi,
  destroyEpub
} = useEpubReader({
  epubContainer,
  tocItems,
  loading,
  t
})

onMounted(async () => {
  _bookId = parseInt(route.params.book_id) || 0
  _fileId = parseInt(route.params.file_id) || 0
  _format = (route.params.format || 'pdf').toLowerCase()
  formatType.value = _format

  let streamUrl = `/api/v1/stream/${_fileId}`

  let savedLocation = null
  try {
    const progress = await request.get(`/progress/${_bookId}/${_fileId}`)
    if (progress && progress.location) {
      savedLocation = progress.location
    }
  } catch (e) { /* ignore */ }

  if (_format === 'pdf') {
    if (savedLocation) {
      currentPage.value = parseInt(savedLocation) || 1
      jumpPageInput.value = currentPage.value
    }
    await initPdf(streamUrl)
  } else if (_format === 'epub') {
    await initEpub(streamUrl, savedLocation)
  }

  // Start progress timer only after init completes so totalPages is accurate
  progressTimer = setInterval(saveProgress, 10000)
})

onBeforeUnmount(() => {
  if (progressTimer) {
    clearInterval(progressTimer)
    progressTimer = null
  }
  saveProgress()
  destroyPdf()
  destroyEpub()
})

watch(currentPage, (val) => {
  jumpPageInput.value = val
})

watch(totalPages, (val) => {
  if (!isPdf.value || !val) return
  const clamped = Math.min(Math.max(parseInt(currentPage.value) || 1, 1), val)
  if (currentPage.value !== clamped) currentPage.value = clamped
  if (jumpPageInput.value !== clamped) jumpPageInput.value = clamped
})

const handleTocClick = (item) => {
  if (item.type === 'epub') {
    jumpToEpubHref(item.href)
  } else if (item.type === 'pdf') {
    jumpToPage(item.page, saveProgress)
  }
}

const saveProgress = async () => {
  if (!_bookId || !_fileId) return
  let location = ''
  let progressPercent = null
  if (_format === 'pdf') {
    location = String(currentPage.value)
    if (totalPages.value > 0) {
      progressPercent = Math.min(100, Math.round((currentPage.value / totalPages.value) * 10000) / 100)
    }
  } else if (_format === 'epub') {
    location = getEpubCfi()
  }
  if (!location) return

  try {
    await request.post('/progress', {
      book_id: _bookId,
      file_id: _fileId,
      location: location,
      progress_percent: progressPercent,
      device_name: navigator.userAgent.split(/[()]/)[1] || navigator.platform || null,
    })
  } catch (e) { /* ignore */ }
}

const goBack = () => {
  router.push('/')
}
</script>

<style scoped>
.reader-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: #fafafa;
  overflow: hidden;
}

.reader-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 48px;
  padding: 0 20px;
  background: #fff;
  border-bottom: 1px solid #ebeef5;
  flex-shrink: 0;
  z-index: 10;
}

.toolbar-left, .toolbar-right {
  flex: 1;
  display: flex;
  align-items: center;
}

.toolbar-left {
  justify-content: flex-start;
  gap: 8px;
}

.toolbar-right {
  justify-content: flex-end;
}

.toolbar-center {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.page-indicator {
  font-size: 14px;
  color: #606266;
  min-width: 50px;
  text-align: center;
}

.page-input {
  width: 100px;
}

/* Body: sidebar + main */
.reader-body {
  flex: 1;
  display: flex;
  overflow: hidden;
}

/* TOC 侧边栏 */
.toc-sidebar {
  width: 260px;
  flex-shrink: 0;
  background: #fff;
  border-right: 1px solid #ebeef5;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.toc-header {
  padding: 14px 16px;
  font-weight: 600;
  font-size: 15px;
  color: #303133;
  border-bottom: 1px solid #ebeef5;
  flex-shrink: 0;
}

.toc-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.toc-item {
  padding: 8px 12px;
  font-size: 13px;
  color: #606266;
  cursor: pointer;
  line-height: 1.5;
  transition: background 0.15s, color 0.15s;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.toc-item:hover {
  background: #ecf5ff;
  color: #409eff;
}

.toc-empty {
  padding: 24px 16px;
  color: #c0c4cc;
  font-size: 13px;
  text-align: center;
}

/* 阅读主区域 */
.reader-main {
  flex: 1;
  overflow: auto;
  position: relative;
  display: flex;
  justify-content: center;
}

/* PDF 连续滚动 */
.pdf-viewer {
  width: 100%;
  max-width: 900px;
  padding: 20px;
}

.pdf-page-wrapper {
  margin-bottom: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  background: #fff;
}

.pdf-canvas {
  width: 100%;
  display: block;
}

.pdf-init-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 0;
  color: #909399;
  gap: 12px;
}

/* EPUB */
.epub-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
  max-width: 900px;
}

.epub-viewer {
  width: 100%;
  height: 100%;
}

.epub-click-zone {
  position: absolute;
  top: 0;
  width: 15%;
  height: 100%;
  z-index: 5;
  cursor: pointer;
  user-select: none;
  -webkit-user-select: none;
}

.epub-click-left {
  left: 0;
}

.epub-click-right {
  right: 0;
}

/* 加载遮罩 */
.loading-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.9);
  z-index: 100;
}

.loading-overlay p {
  margin-top: 16px;
  color: #909399;
  font-size: 14px;
}
</style>
