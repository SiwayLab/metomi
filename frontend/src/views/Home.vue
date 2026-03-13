<template>
  <div class="home-container">
    <header class="home-header">
      <div class="logo-area">
        <h1>{{ systemName }}</h1>
      </div>

      <div class="omni-bar-container">
        <el-input
          v-model="searchQuery"
          :placeholder="$t('home.search_placeholder')"
          class="omni-input"
          size="large"
          clearable
          @keyup.enter="handleOmniAction"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </div>

      <div class="action-area">
        <transition-group name="fade" tag="div" class="edit-actions-wrapper">
          <el-button 
            v-if="appStore.uiMode === 'edit'" 
            key="custom-btn"
            type="success" 
            plain
            :icon="MagicStick" 
            round
            @click="generateCustomCodeDoc"
            class="custom-code-btn"
          >
            {{ $t('home.new_custom_code') }}
          </el-button>

          <el-upload
            v-if="appStore.uiMode === 'edit'"
            key="upload-btn"
            action="/api/v1/upload"
            :with-credentials="true"
            :show-file-list="false"
            :on-success="handleUploadSuccess"
            :on-error="handleUploadError"
            :before-upload="beforeUpload"
            accept=".pdf,.epub"
            class="upload-btn-wrapper"
          >
            <el-button type="primary" :icon="Upload" :loading="uploading" round>{{ $t('home.import_ebook') }}</el-button>
          </el-upload>
        </transition-group>

        <el-dropdown @command="handleMenuCommand" trigger="click">
          <el-button circle class="hamburger-btn">
            <el-icon><Menu /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item disabled class="menu-group-title">
                <el-icon><Sort /></el-icon>{{ $t('home.sort_by') }}
              </el-dropdown-item>
              <el-dropdown-item command="sort_recent" :class="{ 'is-active-sort': sortMode === 'recent' }">
                <el-icon :style="{ visibility: sortMode === 'recent' ? 'visible' : 'hidden' }"><Check /></el-icon><span>{{ $t('home.sort_recent') }}</span>
              </el-dropdown-item>
              <el-dropdown-item command="sort_pub_date" :class="{ 'is-active-sort': sortMode === 'pub_date' }">
                <el-icon :style="{ visibility: sortMode === 'pub_date' ? 'visible' : 'hidden' }"><Check /></el-icon><span>{{ $t('home.sort_pub_date') }}</span>
              </el-dropdown-item>
              <el-dropdown-item command="sort_title_az" :class="{ 'is-active-sort': sortMode === 'title_az' }">
                <el-icon :style="{ visibility: sortMode === 'title_az' ? 'visible' : 'hidden' }"><Check /></el-icon><span>{{ $t('home.sort_title_az') }}</span>
              </el-dropdown-item>
              <el-dropdown-item command="sort_read_status" :class="{ 'is-active-sort': sortMode === 'read_status' }">
                <el-icon :style="{ visibility: sortMode === 'read_status' ? 'visible' : 'hidden' }"><Check /></el-icon><span>{{ $t('home.sort_read_status') }}</span>
              </el-dropdown-item>
              
              <el-dropdown-item divided command="toggleMode">
                <el-icon><Tools /></el-icon>
                {{ appStore.uiMode === 'view' ? $t('home.enter_edit_mode') : $t('home.exit_edit_mode') }}
              </el-dropdown-item>
              <el-dropdown-item command="openSettings">
                <el-icon><Setting /></el-icon>
                {{ $t('home.settings') }}
              </el-dropdown-item>
              <el-dropdown-item divided command="logout" class="danger-text">
                <el-icon><SwitchButton /></el-icon>
                {{ $t('home.logout') }}
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </header>

    <main class="main-content" v-loading.fullscreen.lock="scraping" :element-loading-text="$t('home.scraping_loading')">
      <div v-if="books.length === 0 && !loading" class="empty-state">
        <el-empty :description="$t('home.empty_library')" />
      </div>
      
      <!-- Loading Skeleton Stack -->
      <div v-else-if="loading && books.length === 0" class="book-grid">
        <div v-for="n in 12" :key="`skeleton-${n}`" class="book-card-skeleton">
          <el-skeleton animated>
            <template #template>
              <el-skeleton-item variant="image" style="width: 100%; aspect-ratio: 0.7; border-radius: 8px;" />
              <div style="padding: 14px 0 0;">
                <el-skeleton-item variant="p" style="width: 90%; height: 18px" />
                <el-skeleton-item variant="p" style="width: 60%; height: 14px; margin-top: 8px;" />
              </div>
            </template>
          </el-skeleton>
        </div>
      </div>

      <div v-else class="book-grid" ref="scrollContainer" v-infinite-scroll="loadMoreBooks" :infinite-scroll-disabled="loading || noMore" :infinite-scroll-distance="100">
        <div
          v-for="book in books" 
          :key="book.id" 
          class="book-card"
          @click="openDrawer(book)"
        >
          <div class="cover-wrapper">
            <el-image 
              v-if="book.cover_path" 
              :src="getCoverUrl(book.cover_path)" 
              class="cover-img" 
              lazy 
              fit="cover"
            >
              <template #placeholder>
                <div class="image-slot" style="display: flex; justify-content: center; align-items: center; width: 100%; height: 100%; background: #f5f7fa; color: #a8abb2;">
                  <el-icon><Picture /></el-icon>
                </div>
              </template>
            </el-image>
            <div v-else class="cover-fallback">
              <span>{{ book.title ? book.title.charAt(0).toUpperCase() : 'B' }}</span>
            </div>
            
            <div class="status-tags">
              <el-tag 
                v-if="book.read_status" 
                size="small" 
                effect="dark"
                :type="getStatusType(book.read_status)"
                class="status-tag"
              >
                {{ $t('bookDetail.status_map.' + book.read_status) }}
              </el-tag>
            </div>
          </div>
          
          <div class="book-info">
            <div class="book-title" :title="book.title">{{ book.title }}</div>
            <div class="book-author" :title="getAuthorsStr(book)">
              {{ getAuthorsStr(book) || $t('home.unknown_author') }}
            </div>
          </div>
        </div>
      </div>
      
    </main>

    <BookDetailModal 
      v-model="drawerVisible" 
      :book="selectedBook" 
      @updated="fetchBooks"
    />

    <SettingsDrawer 
      v-model="settingsVisible"
      @system-name-changed="(name) => systemName = name"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { Search, Menu, Setting, Tools, SwitchButton, Upload, Sort, MagicStick, Warning, Check, Loading } from '@element-plus/icons-vue'
import request from '@/utils/request'
import { useUserStore } from '@/store/user'
import { useAppStore } from '@/store/app'
import { useSettingsStore } from '@/store/settings'
import BookDetailModal from '@/components/BookDetailModal.vue'
import SettingsDrawer from '@/components/SettingsDrawer.vue'

const getCoverUrl = (url) => {
  if (!url) return ''
  if (url.startsWith('http')) {
    return `/api/v1/scrape/proxy-image?url=${encodeURIComponent(url)}`
  }
  return url
}

const { t } = useI18n()
const router = useRouter()
const userStore = useUserStore()
const appStore = useAppStore()
const settingsStore = useSettingsStore()

// State
const systemName = ref('Metomi')
const customCodePrefix = ref('MTM-')
const searchQuery = ref('')
const scraping = ref(false)
const uploading = ref(false)
const loading = ref(false)

const books = ref([])
const totalBooks = ref(0)
const currentPage = ref(1)
const pageSize = ref(50)
const sortMode = ref('recent')

const drawerVisible = ref(false)
const selectedBook = ref(null)
const settingsVisible = ref(false)

// Computed Hooks

const noMore = computed(() => {
  return books.value.length > 0 && books.value.length >= totalBooks.value
})

const loadMoreBooks = () => {
  if (loading.value || noMore.value) return
  currentPage.value++
  fetchBooks(true)
}

import { debounce } from 'lodash-es'

// Reset pagination when search/sort changes, with 300ms debounce
watch([searchQuery, sortMode], debounce(() => {
  // 优化：如果是输入自定义编码或者 ISBN，则不去触发全文搜索以防闪烁
  const isCustomCode = searchQuery.value.startsWith(customCodePrefix.value)
  const isIsbn = /^[0-9-]{10,17}$/.test(searchQuery.value)
  
  if (isCustomCode || isIsbn) {
    return
  }
  
  currentPage.value = 1
  fetchBooks(false)
}, 300))

onMounted(async () => {
  try {
    const settings = await settingsStore.fetchSettings(true)
    systemName.value = settingsStore.getSetting('system_name', 'Metomi')
    customCodePrefix.value = settingsStore.getSetting('custom_code_prefix', 'MTM-')
  } catch (error) {
    console.warn('Load settings failed')
    ElMessage.error('加载系统配置失败')
  }
  fetchBooks()
})

let fetchAbortController = null

const fetchBooks = async (append = false) => {
  if (!append && loading.value) {
    if (fetchAbortController) {
      fetchAbortController.abort()
    }
  }
  if (append && loading.value) return

  fetchAbortController = new AbortController()
  loading.value = true
  
  try {
    const res = await request.get('/books', {
      signal: fetchAbortController.signal,
      params: {
        page: currentPage.value,
        page_size: pageSize.value,
        q: searchQuery.value.trim(),
        sort: sortMode.value
      }
    })
    
    if (append) {
      books.value = [...books.value, ...(res.items || [])]
    } else {
      books.value = res.items || []
    }
    
    totalBooks.value = res.total || 0
  } catch (error) {
    if (error.name === 'CanceledError' || error.message === 'canceled') {
      return // 请求被取消时静默，不要重置 loading，让新请求接管
    }
    ElMessage.error(error.response?.data?.detail || '获取书库列表失败')
  } finally {
    loading.value = false
  }
}

const isIsbnFormat = (str) => {
  const cleanStr = str.replace(/-/g, '').trim()
  return /^(978|979)?\d{9}[\dXx]$/i.test(cleanStr) && (cleanStr.length === 10 || cleanStr.length === 13)
}

const handleOmniAction = async () => {
  const q = searchQuery.value.trim()
  if (!q) return

  // 自编码匹配逻辑 (比如: ^MTM-[0-9A-Fa-f]+$)
  // 如果输入以获取的自编码前缀开头，且本地没搜到，则直接占位入库
  const isCustomCode = q.toUpperCase().startsWith(customCodePrefix.value.toUpperCase())
  
  if (isCustomCode) {
    // 先主动搜索一次，看库中是否已有该自编码
    try {
      const searchRes = await request.get('/books', { params: { q, page: 1, page_size: 1 } })
      if (searchRes.total > 0) {
        // 已有匹配，直接展示搜索结果
        currentPage.value = 1
        books.value = searchRes.items || []
        totalBooks.value = searchRes.total || 0
        return
      }
    } catch (_) { /* 搜索失败时仍尝试创建 */ }

    try {
      const bookData = {
        title: t('home.unnamed_doc'),
        custom_code: q.toUpperCase(),
        book_type: 'physical',
        file_id: null
      }
      const savedBook = await request.post('/books', bookData)
      ElMessage({ message: t('home.custom_code_created'), type: 'success', duration: 1500 })
      searchQuery.value = ''
      await fetchBooks()
    } catch (e) {
      ElMessage.error(e.message || t('home.custom_code_create_failed'))
    }
    return
  }

  // ISBN 命中逻辑：先搜索库中是否已有该 ISBN
  if (isIsbnFormat(q)) {
    try {
      const searchRes = await request.get('/books', { params: { q, page: 1, page_size: 1 } })
      if (searchRes.total > 0) {
        // 已有匹配，直接展示搜索结果
        currentPage.value = 1
        books.value = searchRes.items || []
        totalBooks.value = searchRes.total || 0
        return
      }
    } catch (_) { /* 搜索失败时仍尝试刮削 */ }

    await performSilentScrape(q)
    return
  }

  // 其他普通文本：触发搜索
  currentPage.value = 1
  await fetchBooks()
}

// 主动生成自编码 (Edit 模式下)
const generateCustomCodeDoc = async () => {
  try {
    // 生成逻辑：前缀 + 6位随机大写 Hex
    const randomHex = Math.floor(Math.random() * 0xFFFFFF).toString(16).toUpperCase().padStart(6, '0')
    const newCode = `${customCodePrefix.value}${randomHex}`
    
    const bookData = {
      title: t('home.new_custom_doc'),
      custom_code: newCode,
      book_type: 'physical'
    }
    
    const savedBook = await request.post('/books', bookData)
    ElMessage({ message: t('home.custom_code_assigned', { code: newCode }), type: 'success', duration: 1500 })
    
    await fetchBooks()
    
    const newBookInstance = books.value.find(b => b.id === savedBook.id) || savedBook
    openDrawer(newBookInstance)
    
  } catch (e) {
    ElMessage.error(e.message || t('home.generate_failed'))
  }
}

const performSilentScrape = async (isbn) => {
  if (scraping.value) return
  scraping.value = true
  try {
    const submitRes = await request.post('/scrape', { query: isbn })
    const taskId = submitRes.task_id
    
    let status = 'processing'
    let scrapeResult = null
    
    while (status === 'processing') {
      await new Promise(r => setTimeout(r, 1500))
      const statusRes = await request.get(`/scrape/status/${taskId}`)
      status = statusRes.status
      if (status === 'completed') {
        scrapeResult = statusRes.result
      } else if (status === 'failed') {
        throw new Error(statusRes.error || t('home.scrape_not_found'))
      }
    }
    
    if (scrapeResult) {
       const scrapeTitle = scrapeResult.title || t('home.unknown_title')
       
       try {
         await ElMessageBox.confirm(
           t('home.scrape_confirm_msg', { title: scrapeTitle }),
           t('home.scrape_confirm_title'),
           {
             confirmButtonText: t('home.scrape_confirm_yes'),
             cancelButtonText: t('home.scrape_confirm_no'),
             type: 'info',
           }
         )
       } catch {
         // User cancelled
         return
       }

       const bookData = {
          title: scrapeTitle,
          isbn: scrapeResult.isbn || '',
          douban_id: scrapeResult.douban_id || '',
          description: scrapeResult.description || '',
          pub_date: scrapeResult.pub_date || '',
          language: scrapeResult.language || '',
          cover_path: scrapeResult.cover_url || '',
          rating: scrapeResult.rating,
          author_names: scrapeResult.authors || [],
          publisher_name: scrapeResult.publisher || '',
          book_type: 'physical',
          file_id: null
       }
       
       const savedBook = await request.post('/books', bookData)
       ElMessage({ message: t('home.scrape_success', { title: savedBook.title }), type: 'success', duration: 1500 })
       
       searchQuery.value = ''
       fetchBooks()
    }
  } catch (error) {
    const msg = error.message || t('home.network_error')
    ElMessage.error(t('home.scrape_failed', { msg }))
  } finally {
    scraping.value = false
  }
}

// 菜单下拉指令
const handleMenuCommand = (command) => {
  if (command.startsWith('sort_')) {
    sortMode.value = command.replace('sort_', '')
    return
  }

  if (command === 'toggleMode') {
    appStore.toggleMode()
    ElMessage({ message: appStore.uiMode === 'view' ? t('home.switched_to_view') : t('home.switched_to_edit'), type: 'success', duration: 1500 })
  } else if (command === 'openSettings') {
    settingsVisible.value = true
  } else if (command === 'logout') {
    userStore.logout()
    router.push('/login')
  }
}

// 导入
const beforeUpload = (file) => {
  const isAllowed = file.type === 'application/pdf' || file.name.endsWith('.epub')
  if (!isAllowed) {
    ElMessage.error(t('home.upload_pdf_epub_only'))
    return false
  }
  uploading.value = true
  return true
}

const handleUploadSuccess = async (res, uploadFile) => {
  uploading.value = false
  try {
    const rawName = uploadFile?.name || 'unknown'
    const title = rawName.replace(/\.[^/.]+$/, '')
    
    if (res.is_duplicate) {
      ElMessage.warning(t('home.import_duplicate', { title }))
      await fetchBooks()
      return
    }

    const bookData = {
      title: title,
      file_id: res.file_id,
      author_names: [],
    }
    const savedBook = await request.post('/books', bookData)
    ElMessage({ message: t('home.import_success', { title: savedBook.title }), type: 'success', duration: 1500 })
  } catch (error) {
    ElMessage.warning(t('home.upload_success_book_fail'))
  }
  await fetchBooks()
}

const handleUploadError = (err) => {
  uploading.value = false
  try {
    const errorMsg = JSON.parse(err.message)?.detail || t('home.upload_failed')
    ElMessage.error(errorMsg)
  } catch {
    ElMessage.error(t('home.upload_retry'))
  }
}

const openDrawer = (book) => {
  selectedBook.value = book
  drawerVisible.value = true
}

const getAuthorsStr = (book) => {
  if (!book.authors || !book.authors.length) return ''
  return book.authors.map(a => a.name).join(', ')
}

const getStatusType = (status) => {
  const map = {
    'read': 'success',
    'reading': 'primary',
    'unread': 'info',
    'want_to_read': 'warning',
    'skimmed': 'warning',
    'shelved': 'danger'
  }
  return map[status] || 'info'
}
</script>

<style scoped>
.home-container {
  min-height: 100vh;
  width: 100%;
  display: flex;
  flex-direction: column;
}

/* 顶部 Header */
.home-header {
  position: sticky;
  top: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 80px;
  padding: 0 40px;
  background: rgba(255, 255, 255, 0.45);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.6);
  box-shadow: 0 4px 30px rgba(0, 0, 0, 0.03);
  gap: 16px;
  min-width: 0;
}

.logo-area h1 {
  margin: 0;
  font-size: 26px;
  font-weight: 800;
  color: #1a1a1a;
  letter-spacing: -0.5px;
}

/* 中间 Omni Bar */
.omni-bar-container {
  flex: 1 1 280px;
  min-width: 0;
  max-width: 600px;
  margin: 0 40px;
}

/* 圆角药丸形搜索框 */
.omni-input :deep(.el-input__wrapper) {
  border-radius: 50px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.1);
  background: rgba(255, 255, 255, 0.65);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.5);
  padding: 0 20px;
}

.omni-input :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08), 0 0 0 1px var(--el-color-primary) inset;
}

/* 右侧按钮区 */
.action-area {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.edit-actions-wrapper {
  display: flex;
  align-items: center;
}

.custom-code-btn {
  margin-right: 12px;
}

.upload-btn-wrapper {
  margin-right: 12px;
}

.hamburger-btn {
  font-size: 18px;
  background: rgba(255, 255, 255, 0.65);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.5);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  margin-left: 4px;
}

.hamburger-btn:hover {
  background: rgba(255, 255, 255, 0.85);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.danger-text {
  color: var(--el-color-danger);
}

.menu-group-title {
  font-weight: 600;
  color: #909399;
  letter-spacing: 1px;
}

.is-active-sort {
  color: var(--el-color-primary) !important;
  font-weight: 600;
  background-color: transparent !important;
}

/* 核心主区域 */
.main-content {
  flex: 1;
  padding: 20px 40px 60px 40px; /* 舒适留白 */
  overflow: visible; /* 强制去掉内部滚动条使用最外层滚动条 */
}

.empty-state {
  margin-top: 100px;
}

/* 无边框卡片网格 */
.book-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 32px;
}

.book-card {
  cursor: pointer;
  background: rgba(255, 255, 255, 0.65);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
  display: flex;
  flex-direction: column;
}

.book-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.08);
}

/* 封面封套 */
.cover-wrapper {
  position: relative;
  width: 100%;
  aspect-ratio: 3 / 4;
  background-color: rgba(0, 0, 0, 0.03);
  overflow: hidden;
}

.cover-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.5s ease;
}

.book-card:hover .cover-img {
  transform: scale(1.05);
}

.cover-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 72px;
  color: #dcdfe6;
  font-weight: 800;
  font-family: monospace;
}

.status-tags {
  position: absolute;
  top: 12px;
  right: 12px;
}

.status-tag {
  border-radius: 12px;
  font-weight: 600;
  letter-spacing: 1px;
  padding: 0 10px;
}

/* 文本信息 */
.book-info {
  padding: 16px;
}

.book-title {
  font-size: 16px;
  font-weight: 700;
  color: #2c3e50;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 4px;
}

.book-author {
  font-size: 13px;
  color: #909399;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Vue 过渡动画类 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

@media (max-width: 1024px) {
  .home-header {
    height: auto;
    padding: 16px 20px;
    flex-wrap: wrap;
    align-items: stretch;
  }

  .logo-area {
    width: 100%;
  }

  .omni-bar-container {
    order: 2;
    flex: 1 1 100%;
    max-width: 100%;
    margin: 0;
  }

  .action-area {
    order: 3;
    width: 100%;
    justify-content: space-between;
  }

  .main-content {
    padding: 20px 20px 36px;
  }
}

@media (max-width: 640px) {
  .home-header {
    padding: 12px;
  }

  .logo-area h1 {
    font-size: 22px;
  }

  .main-content {
    padding: 16px 12px 24px;
  }

  .book-grid {
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 16px;
  }
}
</style>
