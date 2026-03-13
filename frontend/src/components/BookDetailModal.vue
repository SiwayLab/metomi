<template>
  <el-dialog
    v-model="visible"
    width="720px"
    class="book-glass-modal"
    :align-center="true"
    :show-close="false"
    @closed="handleClosed"
  >
    <!-- Modal Actions (Top Right) -->
    <div class="modal-top-actions">
      <el-button 
        v-if="!isEditMode" 
        class="top-edit-btn" 
        type="primary" 
        plain 
        round 
        icon="Edit" 
        size="small"
        @click="localEditMode = true"
      >
        {{ $t('common.edit') }}
      </el-button>
      <div class="modal-close-btn" @click="visible = false">
        <el-icon><Close /></el-icon>
      </div>
    </div>

    <div class="modal-content-wrapper" v-if="bookData" v-loading="saving || deleting">
      
      <!-- Top Section -->
      <div class="top-section">
        <!-- Left: Cover -->
        <div 
          class="cover-block" 
          :class="{ 'is-editable': isEditMode }"
          @click="handleCoverClickProxy"
        >
          <img v-if="form.cover_path" :src="getCoverUrl(form.cover_path)" class="book-cover" loading="lazy" />
          <div v-else class="cover-placeholder">
            <el-icon :size="32"><Picture /></el-icon>
            <span>{{ $t('bookDetail.no_cover') }}</span>
          </div>
          
          <!-- Hover Overlay (Edit Mode: Camera | View Mode (w/ file): Read) -->
          <div class="cover-overlay" v-if="isEditMode">
            <el-icon :size="32"><Camera /></el-icon>
            <span>{{ $t('bookDetail.change_cover') }}</span>
          </div>
          <div class="cover-overlay read-overlay" v-else-if="hasFile" @click.stop="goRead">
            <el-icon :size="32"><CaretRight /></el-icon>
            <span>{{ $t('bookDetail.read_book') }}</span>
          </div>
        </div>
        
        <input 
          type="file" 
          ref="coverInput" 
          style="display: none" 
          accept="image/jpeg,image/png,image/webp"
          @change="handleCoverChange"
        />

        <!-- Right: Title & Author -->
        <div class="top-info-block">
          <div class="form-row">
            <label class="field-label">{{ $t('bookDetail.title') }}</label>
            <el-input 
              v-if="isEditMode" 
              v-model="form.title" 
              class="large-input" 
              :placeholder="$t('bookDetail.title_placeholder')"
            />
            <div v-else class="readonly-value text-xl font-bold">{{ form.title || '--' }}</div>
          </div>

          <div class="form-row">
            <label class="field-label">{{ $t('bookDetail.author') }}</label>
            <el-input 
              v-if="isEditMode" 
              v-model="authorsStr" 
              :placeholder="$t('bookDetail.author_placeholder')" 
            />
            <div v-else class="readonly-value">{{ authorsStr || '--' }}</div>
          </div>

          <!-- Top Section Read Action (View Mode) -->
          <div class="top-read-action" v-if="!isEditMode && hasFile">
             <el-dropdown v-if="bookData.files && bookData.files.length > 1" split-button type="primary" @click="goRead()" @command="goRead" class="top-read-dropdown">
                <el-icon class="el-icon--left"><Reading /></el-icon>
                {{ $t('bookDetail.read_now') }}
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item v-for="file in bookData.files" :key="file.id" :command="file">
                      {{ (file.format || 'unknown').toUpperCase() }} ({{ (file.size_bytes / 1024 / 1024).toFixed(1) }} MB)
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
             </el-dropdown>
             <el-button v-else color="#409eff" class="top-read-btn" @click="goRead()" round>
                <el-icon class="el-icon--left"><Reading /></el-icon>
                {{ $t('bookDetail.read_now') }}
             </el-button>
          </div>
        </div>
      </div>

      <!-- Middle Grid Section -->
      <div class="middle-grid-section">
        <div class="grid-item">
          <label class="field-label">{{ $t('bookDetail.publisher') }}</label>
          <el-input v-if="isEditMode" v-model="form.publisher_name" />
          <div v-else class="readonly-value">{{ form.publisher_name || '--' }}</div>
        </div>
        
        <div class="grid-item">
          <label class="field-label">{{ $t('bookDetail.year') }}</label>
          <el-input v-if="isEditMode" v-model="form.pub_date" />
          <div v-else class="readonly-value">{{ form.pub_date || '--' }}</div>
        </div>
        
        <div class="grid-item">
          <label class="field-label">{{ form.isbn ? 'ISBN' : (form.custom_code ? $t('bookDetail.custom_code') : 'ISBN') }}</label>
          <template v-if="isEditMode">
            <el-input v-if="!form.isbn && form.custom_code" v-model="form.custom_code" />
            <el-input v-else v-model="form.isbn" />
          </template>
          <div v-else class="readonly-value">{{ form.isbn || form.custom_code || '--' }}</div>
        </div>

        <div class="grid-item">
          <label class="field-label">{{ $t('bookDetail.douban_id') }}</label>
          <el-input v-if="isEditMode" v-model="form.douban_id" />
          <div v-else class="readonly-value">{{ form.douban_id || '--' }}</div>
        </div>
        

        <div class="grid-item">
          <label class="field-label">{{ $t('bookDetail.rating') }}</label>
          <el-rate 
            v-if="isEditMode || isFieldEditableInView('rating')"
            v-model="form.rating" 
            :max="5"
            clearable
            @change="!isEditMode && autoSaveField('rating')"
            class="form-rate"
          />
          <div v-else class="readonly-value rate-readonly">
            <el-rate v-model="form.rating" :max="5" disabled class="form-rate" />
          </div>
        </div>
        
        <div class="grid-item full-width-item tags-row">
          <div class="half-row">
            <label class="field-label">{{ $t('bookDetail.read_status') }}</label>
            <el-select 
              v-if="isEditMode || isFieldEditableInView('read_status')"
              v-model="form.read_status" 
              :placeholder="$t('bookDetail.select_placeholder')" 
              clearable
              @change="!isEditMode && autoSaveField('read_status')"
            >
              <el-option :label="$t('bookDetail.status_unread')" value="unread" />
              <el-option :label="$t('bookDetail.status_want')" value="want_to_read" />
              <el-option :label="$t('bookDetail.status_reading')" value="reading" />
              <el-option :label="$t('bookDetail.status_read')" value="read" />
              <el-option :label="$t('bookDetail.status_put_aside')" value="shelved" />
              <el-option :label="$t('bookDetail.status_skimmed')" value="skimmed" />
            </el-select>
            <div v-else class="readonly-value">
              <el-tag v-if="form.read_status" size="small" type="info">{{ $t('bookDetail.status_map.' + form.read_status) }}</el-tag>
              <span v-else>--</span>
            </div>
          </div>
        </div>

        <div class="grid-item full-width-item physical-row">
           <div class="half-row">
             <label class="field-label">{{ $t('bookDetail.format') }}</label>
             <el-checkbox-group v-if="isEditMode" v-model="bookTypeArray" class="custom-checkboxes">
                <el-checkbox label="ebook" value="ebook">{{ $t('bookDetail.format_ebook') }}</el-checkbox>
                <el-checkbox label="physical" value="physical">{{ $t('bookDetail.format_physical') }}</el-checkbox>
             </el-checkbox-group>
             <div v-else class="readonly-value">
               <el-tag v-if="bookTypeArray.includes('ebook')" size="small" type="info" class="mr-2">{{ $t('bookDetail.format_ebook_short') }}</el-tag>
               <el-tag v-if="bookTypeArray.includes('physical')" size="small" type="warning">{{ $t('bookDetail.format_physical_short') }}</el-tag>
               <span v-if="!bookTypeArray.length">--</span>
             </div>
           </div>

           <div class="half-row" v-if="bookTypeArray.includes('physical')">
              <label class="field-label">{{ $t('bookDetail.location') }}</label>
              <el-input 
                v-if="isEditMode || isFieldEditableInView('location')"
                v-model="form.physical_location" 
                :placeholder="$t('bookDetail.location_placeholder')" 
                @blur="!isEditMode && autoSaveField('location')"
              />
              <div v-else class="readonly-value">{{ form.physical_location || '--' }}</div>
           </div>
        </div>

        <!-- Files Display -->
        <div class="grid-item full-width-item files-row" v-if="(bookData.files && bookData.files.length > 0) || isEditMode">
           <label class="field-label">{{ $t('bookDetail.source_files') }}</label>
           <div class="files-container" style="display: flex; flex-wrap: wrap; gap: 8px; align-items: center;">
              <div 
                v-for="file in bookData.files" 
                :key="file.id" 
                class="file-item-group"
              >
                <el-tag 
                  type="success"
                  effect="plain"
                  round
                >
                  {{ file.format.toUpperCase() }} ({{ formatBytes(file.size_bytes) }})
                </el-tag>
                <el-button 
                  v-if="!isEditMode"
                  size="small"
                  type="primary"
                  circle
                  plain
                  icon="Download"
                  :loading="downloadingStatus[file.id]"
                  :title="$t('bookDetail.download')"
                  @click.stop="downloadFile(file)"
                />
                <el-popconfirm
                  v-if="isEditMode"
                  :title="$t('bookDetail.unlink_file_confirm')"
                  :confirm-button-text="$t('bookDetail.unlink')"
                  confirm-button-type="danger"
                  :cancel-button-text="$t('bookDetail.cancel')"
                  @confirm="handleUnlinkFile(file)"
                >
                  <template #reference>
                    <el-button
                      size="small"
                      type="danger"
                      circle
                      plain
                      icon="Delete"
                      :title="$t('bookDetail.unlink_file')"
                    />
                  </template>
                </el-popconfirm>
              </div>

              <el-button 
                v-if="isEditMode" 
                size="small" 
                type="primary" 
                plain 
                round 
                icon="Upload" 
                @click="triggerFileUpload"
                :loading="uploadingFile"
              >
                {{ $t('bookDetail.upload_file') }}
              </el-button>
              
              <input 
                type="file" 
                ref="fileInput" 
                style="display: none" 
                accept=".pdf,.epub"
                @change="handleFileUpload"
              />
           </div>
        </div>
      </div>

      <!-- Bottom Summary Section -->
      <div class="summary-section">
        <label class="field-label">{{ $t('bookDetail.summary') }}</label>
        <el-input 
          v-if="isEditMode"
          v-model="form.description" 
          type="textarea" 
          :rows="4" 
          resize="vertical" 
        />
        <div v-else class="readonly-value description-text">{{ form.description || $t('bookDetail.no_summary') }}</div>
      </div>

      <!-- Actions Section -->
      <div class="action-section" v-if="isEditMode">
        <div class="left-action">
          <el-popconfirm
            :title="$t('bookDetail.delete_confirm')"
            :confirm-button-text="$t('bookDetail.delete')"
            confirm-button-type="danger"
            :cancel-button-text="$t('bookDetail.cancel')"
            icon="Warning"
            icon-color="#f56c6c"
            @confirm="handleDelete"
          >
            <template #reference>
              <el-button type="danger" text>{{ $t('bookDetail.delete_record') }}</el-button>
            </template>
          </el-popconfirm>
        </div>
        <div class="center-actions">
           <el-button color="#E6A23C" plain round icon="MagicStick" @click="openScraperDialog">{{ $t('bookDetail.update_scraper') }}</el-button>
           <el-button @click="handleCancel" round>{{ $t('bookDetail.cancel') }}</el-button>
           <el-button type="primary" @click="handleSave" round>{{ $t('bookDetail.save_changes') }}</el-button>
        </div>
      </div>
      
    </div>

    <ScraperDialog
      v-model="scraperVisible"
      :initial-query="scraperQuery"
      @target-selected="handleScrapeResult"
    />

  </el-dialog>
</template>

<script setup>
import { computed, ref, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Edit, Reading, InfoFilled, Close, SuccessFilled, WarningFilled, Promotion, Delete, Sort } from '@element-plus/icons-vue'
import request from '@/utils/request'

const getCoverUrl = (url) => {
  if (!url) return ''
  if (url.startsWith('http')) {
    return `/api/v1/scrape/proxy-image?url=${encodeURIComponent(url)}`
  }
  return url
}

import { useAppStore } from '@/store/app'
import { useSettingsStore } from '@/store/settings'
import ScraperDialog from './ScraperDialog.vue'
import { useBookForm } from '@/composables/useBookForm'
import { useUploadScraper } from '@/composables/useUploadScraper'

const { t } = useI18n()

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  book: { type: Object, default: null }
})

const emit = defineEmits(['update:modelValue', 'updated'])
const router = useRouter()
const appStore = useAppStore()
const settingsStore = useSettingsStore()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const localEditMode = ref(false)
const isEditMode = computed(() => appStore.uiMode === 'edit' || localEditMode.value)

const bookData = ref(null)
const deleting = ref(false)
const hasFile = computed(() => bookData.value?.files?.length > 0)
const editableFieldsInView = ref([])
const exportFilenameTemplate = ref('{title}')

onMounted(async () => {
  try {
    const res = await settingsStore.fetchSettings()
    
    const fieldsSettingStr = res['view_mode_editable_fields']
    if (fieldsSettingStr) {
      try {
        editableFieldsInView.value = JSON.parse(fieldsSettingStr)
      } catch (e) {
        editableFieldsInView.value = []
      }
    }
    
    const exportTemplateSetting = res['export_filename_template']
    if (exportTemplateSetting) {
      exportFilenameTemplate.value = exportTemplateSetting
    }
  } catch (error) {
    console.warn('Load view_mode_editable_fields failed')
  }
})

const {
  form,
  authorsStr,
  bookTypeArray,
  saving,
  initForm,
  autoSaveField,
  handleSave,
  handleCancel
} = useBookForm({ bookData, localEditMode, visible, t, emit })

watch(() => props.book, (newBook) => {
  initForm(newBook)
}, { immediate: true })

const handleClosed = () => {
  saving.value = false
  localEditMode.value = false
}

const isFieldEditableInView = (field) => {
  return editableFieldsInView.value.includes(field)
}

const handleDelete = async () => {
  if (!bookData.value?.id) return
  deleting.value = true
  try {
    await request.delete(`/books/${bookData.value.id}`)
    ElMessage.success(t('bookDetail.delete_success'))
    emit('updated')
    visible.value = false
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || t('bookDetail.delete_failed', '删除失败'))
  } finally {
    deleting.value = false
  }
}

const handleUnlinkFile = async (file) => {
  if (!bookData.value?.id || !file?.id) return
  try {
    const updated = await request.delete(`/books/${bookData.value.id}/files/${file.id}`)
    bookData.value = updated
    ElMessage.success(t('bookDetail.unlink_success'))
    emit('updated')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || t('bookDetail.unlink_failed'))
  }
}

const goRead = (targetFile) => {
  if (!hasFile.value || isEditMode.value) return
  const file = targetFile && targetFile.id ? targetFile : bookData.value.files[0]
  if (!file) return
  router.push(`/reader/${bookData.value.id}/${file.id}/${file.format}`)
}

const {
  fileInput,
  uploadingFile,
  downloadingStatus,
  coverInput,
  scraperVisible,
  scraperQuery,
  triggerFileUpload,
  handleFileUpload: rawHandleFileUpload,
  deleteFileLink: rawDeleteFileLink,
  downloadFile,
  formatBytes,
  handleCoverClick: rawHandleCoverClick,
  handleCoverChange,
  openScraperDialog,
  handleScrapeResult
} = useUploadScraper(bookData, form, authorsStr, emit, exportFilenameTemplate)

const handleFileUpload = (e) => rawHandleFileUpload(e, initForm)
const deleteFileLink = (fileId) => rawDeleteFileLink(fileId, initForm)
const handleCoverClickProxy = () => rawHandleCoverClick(isEditMode.value, goRead)

</script>

<style scoped>
.file-item-group {
  display: flex;
  align-items: center;
  gap: 4px;
}
/* Top Actions Wrapper */
.modal-top-actions {
  position: absolute;
  top: 20px;
  right: 20px;
  display: flex;
  align-items: center;
  gap: 12px;
  z-index: 10;
}

/* Custom Close Button */
.modal-close-btn {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  color: #606266;
}
.modal-close-btn:hover {
  background: rgba(255, 255, 255, 0.9);
  color: #f56c6c;
}

/* Edit Button Top */
.top-edit-btn {
  background: rgba(255, 255, 255, 0.5) !important;
  backdrop-filter: blur(10px);
  border-color: rgba(64, 158, 255, 0.3) !important;
}
.top-edit-btn:hover {
  background: white !important;
  border-color: rgba(64, 158, 255, 0.8) !important;
}

.modal-content-wrapper {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* Generic Label and Form Elements */
.field-label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: #606266;
  margin-bottom: 6px;
  letter-spacing: 0.5px;
}

.readonly-value {
  font-size: 15px;
  color: #1a1a1a;
  min-height: 32px;
  line-height: 1.5;
  display: flex;
  align-items: center;
}

.text-xl { font-size: 22px; }
.font-bold { font-weight: 700; color: #1a1a1a; }
.hint-text {
  font-weight: 400;
  color: #a8abb2;
  font-size: 12px;
}
.mr-2 { margin-right: 8px; }

/* TOP SECTION */
.top-section {
  display: flex;
  gap: 32px;
  align-items: stretch;
}

.cover-block {
  flex-shrink: 0;
  width: 160px;
  height: 230px;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 12px 24px rgba(0,0,0,0.12);
  position: relative;
  background-color: rgba(0,0,0,0.03);
}

.cover-block.is-editable { cursor: pointer; }
.cover-block.is-editable:hover .cover-overlay { opacity: 1; }

.book-cover {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.cover-placeholder {
  width: 100%;
  height: 100%;
  background: #f0f2f5;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  color: #a8abb2;
  font-size: 13px;
  gap: 8px;
}

.cover-overlay {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.6);
  color: white;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s;
  font-size: 14px;
  gap: 8px;
  backdrop-filter: blur(4px);
}

.cover-block:hover .read-overlay { 
  opacity: 1; 
  cursor: pointer;
}

.top-info-block {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
  justify-content: center; /* Center them perfectly with the cover */
  padding-top: 5px;
  padding-bottom: 5px;
}

.top-read-action {
  margin-top: 10px;
}

.top-read-btn {
  width: auto;
  padding: 0 24px;
  font-weight: 500;
  letter-spacing: 0.5px;
}

.form-row {
  display: flex;
  flex-direction: column;
}

/* MIDDLE GRID SECTION */
.middle-grid-section {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px 24px;
  padding: 20px 0;
  border-top: 1px solid rgba(0,0,0,0.05);
  border-bottom: 1px solid rgba(0,0,0,0.05);
}

.grid-item {
  display: flex;
  flex-direction: column;
}

.full-width-item {
  grid-column: 1 / -1;
}

.half-row {
  flex: 1;
}
.tags-row, .physical-row {
  display: flex;
  flex-direction: row;
  gap: 24px;
}

.form-rate {
  height: 32px;
  display: flex;
  align-items: center;
}

/* SUMMARY SECTION */
.summary-section {
  display: flex;
  flex-direction: column;
}
.description-text {
  white-space: pre-wrap;
  color: #303133;
  font-size: 14px;
  line-height: 1.6;
}

/* ACTIONS SECTION */
.action-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
}
.center-actions {
  display: flex;
  gap: 12px;
}
.view-mode-actions {
  justify-content: center;
  margin-top: 16px;
}
.view-mode-actions .read-btn {
  width: 200px;
  font-size: 15px;
  letter-spacing: 1px;
}

/* --- Mobile Responsiveness --- */
@media (max-width: 768px) {
  /* Let the dialog body be smaller and adjust padding */
  :deep(.el-dialog.book-glass-modal) {
    width: 90% !important;
    margin: 5vh auto !important;
  }
  
  :deep(.book-glass-modal .el-dialog__body) {
    padding: 20px 20px !important;
  }

  /* Stack cover and book info */
  .top-section {
    flex-direction: column;
    align-items: center;
    gap: 20px;
  }

  .cover-block {
    width: 140px;
    height: 200px;
  }

  /* Center the title/author info on mobile */
  .top-info-block {
    align-items: center;
    text-align: center;
    width: 100%;
  }

  .form-row {
    width: 100%;
    align-items: center;
  }

  /* Make grid single column */
  .middle-grid-section {
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .tags-row, .physical-row {
    flex-direction: column;
    gap: 16px;
  }
  
  .half-row {
    width: 100%;
  }

  /* Make actions stack if needed */
  .action-section {
    flex-direction: column;
    gap: 16px;
  }
  .center-actions {
    flex-wrap: wrap;
    justify-content: center;
  }
}
</style>
