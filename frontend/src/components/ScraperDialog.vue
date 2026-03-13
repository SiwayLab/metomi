<template>
  <el-dialog 
    v-model="visible" 
    :title="$t('bookDetail.scraper_title')" 
    width="500px"
    append-to-body
    class="nested-glass-dialog"
    @open="onOpen"
  >
    <el-input 
      v-model="scraperQuery" 
      :placeholder="$t('bookDetail.scraper_placeholder')"
      @keyup.enter="startSearchCandidates"
    >
      <template #append>
        <el-button :loading="scrapingRef" @click="startSearchCandidates">{{ $t('bookDetail.scraper_search') }}</el-button>
      </template>
    </el-input>

    <div v-if="scrapingRef" class="scraper-loading">
      <el-icon class="is-loading" :size="24"><Loading /></el-icon>
      <p>{{ scrapingMsg }}</p>
    </div>

    <div v-else-if="candidates.length > 0" class="candidate-list">
      <div 
        v-for="(item, index) in candidates" 
        :key="index"
        class="candidate-item"
        @click="selectCandidate(item)"
      >
        <img v-if="item.cover_url" :src="getCoverUrl(item.cover_url)" class="candidate-cover" />
        <div v-else class="candidate-cover-placeholder"><el-icon><Picture /></el-icon></div>
        <div class="candidate-info">
          <div class="candidate-title">{{ item.title }}</div>
          <div class="candidate-meta">
            <span v-if="item.authors?.length">{{ item.authors.join(', ') }}</span>
            <span v-if="item.publisher"> | {{ item.publisher }}</span>
          </div>
          <div class="candidate-source">
            <el-tag size="small" type="info">{{ item.source }}</el-tag>
          </div>
        </div>
      </div>
    </div>
    
    <div v-else-if="searchDone && candidates.length === 0" class="scraper-loading">
      <p>{{ $t('bookDetail.scraper_no_results') }}</p>
    </div>
  </el-dialog>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Loading, Picture } from '@element-plus/icons-vue'
import request from '@/utils/request'

const getCoverUrl = (url) => {
  if (!url) return ''
  if (url.startsWith('http')) {
    // Proxy external URLs through backend to fix 403 Forbidden hotlink blocks
    return `/api/v1/scrape/proxy-image?url=${encodeURIComponent(url)}`
  }
  return url
}

const { t } = useI18n()

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  initialQuery: { type: String, default: '' }
})

const emit = defineEmits(['update:modelValue', 'target-selected'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const scraperQuery = ref('')
const scrapingRef = ref(false)
const scrapingMsg = ref('')
const candidates = ref([])
const searchDone = ref(false)

const onOpen = () => {
  scraperQuery.value = props.initialQuery
  candidates.value = []
  searchDone.value = false
}

const startSearchCandidates = async () => {
  if (!scraperQuery.value.trim()) {
    return ElMessage.warning(t('bookDetail.scraper_keyword_required'))
  }
  
  scrapingRef.value = true
  scrapingMsg.value = t('bookDetail.scraper_searching')
  searchDone.value = false
  candidates.value = []
  
  try {
    const res = await request.post('/scrape/search/candidates', { query: scraperQuery.value.trim() })
    candidates.value = res.candidates || []
    searchDone.value = true
  } catch (err) {
    ElMessage.error(err.message || t('bookDetail.scraper_error'))
  } finally {
    scrapingRef.value = false
  }
}

const selectCandidate = async (candidate) => {
  scrapingRef.value = true
  scrapingMsg.value = t('bookDetail.scraper_searching')
  
  try {
    const res = await request.post('/scrape/fetch/candidate', {
      source: candidate.source,
      id: candidate.id
    })
    
    const result = res.result
    if (!result || !result.title) throw new Error(t('bookDetail.scraper_no_results'))
    
    let replaceCover = false
    if (result.cover_url) {
      try {
        await ElMessageBox.confirm(
          t('bookDetail.replace_cover_confirm'), 
          t('bookDetail.replace_cover_title'), 
          {
            confirmButtonText: t('bookDetail.replace_cover_yes'),
            cancelButtonText: t('bookDetail.replace_cover_no'),
            type: 'info'
          }
        )
        replaceCover = true
      } catch (e) {
        replaceCover = false
      }
    }
    
    emit('target-selected', { result, replaceCover })
    visible.value = false
  } catch (err) {
    ElMessage.error(err.message || t('bookDetail.scraper_error'))
  } finally {
    scrapingRef.value = false
  }
}
</script>

<style scoped>
:global(.nested-glass-dialog) {
  border-radius: 16px !important;
  background: rgba(255, 255, 255, 0.8) !important;
  backdrop-filter: blur(20px) !important;
}
:global(.nested-glass-dialog .el-dialog__header) {
  border-bottom: none !important;
}
:global(.nested-glass-dialog .el-dialog__footer) {
  border-top: none !important;
}
:global(.nested-glass-dialog .el-input-group) {
  display: flex;
  align-items: stretch;
}
:global(.nested-glass-dialog .el-input-group__append) {
  background-color: rgba(255, 255, 255, 0.5) !important;
  border: 1px solid rgba(0, 0, 0, 0.06) !important;
  border-left: 0 !important;
  border-top-right-radius: 10px !important;
  border-bottom-right-radius: 10px !important;
  color: #606266;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03) !important;
  transition: all 0.25s ease;
}
:global(.nested-glass-dialog .el-input-group > .el-input__wrapper) {
  border-top-right-radius: 0 !important;
  border-bottom-right-radius: 0 !important;
}
.scraper-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 0;
  color: #909399;
  gap: 12px;
}
.candidate-list {
  max-height: 350px;
  overflow-y: auto;
  margin-top: 16px;
}
.candidate-item {
  display: flex;
  padding: 12px;
  border-bottom: 1px solid rgba(0,0,0,0.05);
  cursor: pointer;
  border-radius: 8px;
}
.candidate-item:hover { background: rgba(0,0,0,0.03); }
.candidate-cover { width: 50px; height: 75px; object-fit: cover; border-radius: 4px; margin-right: 12px; }
.candidate-cover-placeholder { width: 50px; height: 75px; background: #f0f2f5; display: flex; justify-content: center; align-items: center; color: #a8abb2; border-radius: 4px; margin-right: 12px; }
.candidate-info { flex: 1; display: flex; flex-direction: column; justify-content: center; }
.candidate-title { font-weight: 600; font-size: 14px; color: #1a1a1a; margin-bottom: 4px; }
.candidate-meta { font-size: 12px; color: #909399; margin-bottom: 6px; }
.candidate-source { margin-top: auto; }
</style>
