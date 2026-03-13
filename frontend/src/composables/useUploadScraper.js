import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'
import { useI18n } from 'vue-i18n'

export function useUploadScraper(bookData, form, authorsStr, emit, exportFilenameTemplate) {
    const { t } = useI18n()

    // File Upload State
    const fileInput = ref(null)
    const uploadingFile = ref(false)
    const downloadingStatus = ref({})

    // Cover Upload State
    const coverInput = ref(null)
    const saving = ref(false)

    // Scraper State
    const scraperVisible = ref(false)
    const scraperQuery = ref('')

    // ----- File Handling -----
    const triggerFileUpload = () => {
        fileInput.value?.click()
    }

    const handleFileUpload = async (e, initForm) => {
        const file = e.target.files?.[0]
        if (!file) return

        const fileName = file.name.toLowerCase()
        if (!fileName.endsWith('.pdf') && !fileName.endsWith('.epub')) {
            ElMessage.warning(t('home.upload_pdf_epub_only'))
            if (fileInput.value) fileInput.value.value = ''
            return
        }

        uploadingFile.value = true
        try {
            const formData = new FormData()
            formData.append('file', file)

            const uploadRes = await request.post('/upload', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            })

            const updateRes = await request.put(`/books/${bookData.value.id}`, { file_id: uploadRes.file_id })

            ElMessage.success(t('bookDetail.file_upload_success'))

            if (updateRes && updateRes.id) {
                initForm(updateRes)
            }
            emit('updated')
        } catch (err) {
            ElMessage.error(err.message || t('home.upload_failed'))
        } finally {
            uploadingFile.value = false
            if (fileInput.value) fileInput.value.value = ''
        }
    }

    const deleteFileLink = async (fileId, initForm) => {
        try {
            saving.value = true
            const updateRes = await request.delete(`/books/${bookData.value.id}/files/${fileId}`)
            ElMessage.success(t('bookDetail.file_unlink_success'))

            if (updateRes && updateRes.id) {
                initForm(updateRes)
            }
            emit('updated')
        } catch (err) {
            const errorMsg = err.response?.data?.detail || err.message || t('common.error')
            ElMessage.error(`删除文件关联失败: ${errorMsg}`)
        } finally {
            saving.value = false
        }
    }

    // ----- Download Handling -----
    const downloadFile = async (file) => {
        if (!file || !file.id) return
        if (downloadingStatus.value[file.id]) return

        downloadingStatus.value[file.id] = true

        try {
            // Parse formatting mapping to generate desired filename
            let generatedName = exportFilenameTemplate ? exportFilenameTemplate.value : '{title}';
            const mapObj = {
                '{title}': form.value.title || 'book',
                '{authors}': bookData.value?.authors?.length ? bookData.value.authors.map(a => a.name).join('; ') : 'Unknown',
                '{year}': form.value.pub_date ? form.value.pub_date.substring(0, 4) : 'Year',
                '{publisher}': form.value.publisher_name || 'Publisher',
                '{isbn}': form.value.isbn || 'ISBN',
                '{douban_id}': form.value.douban_id || 'DoubanID',
                '{custom_code}': form.value.custom_code || 'CustomCode'
            };

            generatedName = generatedName.replace(/{title}|{authors}|{year}|{publisher}|{isbn}|{douban_id}|{custom_code}/gi, function (matched) {
                return mapObj[matched] || matched;
            });

            const safeTitle = (generatedName || form.value.title || 'book').replace(/[\\/:*?"<>|]/g, '_');
            const fileName = `${safeTitle}.${file.format.toLowerCase()}`;

            // Because the backend API uses HttpOnly cookies for authentication,
            // we can trigger a native browser download just by creating an <a> link.
            // This allows the browser's native download manager (like Z-Library's experience)
            // to capture the task and show the progress bar to the user, instead of 
            // doing an invisible AJAX download into memory.
            const downloadUrl = `/api/v1/stream/${file.id}?download=${encodeURIComponent(fileName)}`;

            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = downloadUrl;
            a.setAttribute('download', fileName);
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);

        } catch (error) {
            ElMessage.error(t('bookDetail.download_failed', '下载失败'));
        } finally {
            // Give short timeout so the spinner disappears after the browser captures it
            setTimeout(() => {
                downloadingStatus.value[file.id] = false;
            }, 500);
        }
    }

    const formatBytes = (bytes, decimals = 2) => {
        if (!bytes) return '0 B'
        const k = 1024
        const dm = decimals < 0 ? 0 : decimals
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
        const i = Math.floor(Math.log(bytes) / Math.log(k))
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i]
    }

    // ----- Cover Handling -----
    const handleCoverClick = (isEditMode, goRead) => {
        if (isEditMode) {
            if (!saving.value) coverInput.value?.click()
        } else {
            goRead()
        }
    }

    const handleCoverChange = async (e) => {
        const file = e.target.files?.[0]
        if (!file) return

        if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
            return ElMessage.warning(t('bookDetail.cover_format_hint'))
        }

        const formData = new FormData()
        formData.append('cover', file)

        try {
            saving.value = true
            const res = await request.post(`/books/${bookData.value.id}/cover`, formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            })
            ElMessage.success(t('bookDetail.cover_update_success'))
            form.value.cover_path = res.cover_path
            emit('updated')
        } catch (err) {
            ElMessage.error(err.message || t('bookDetail.cover_upload_failed'))
        } finally {
            saving.value = false
            if (coverInput.value) coverInput.value.value = ''
        }
    }

    // ----- Scraper Handling -----
    const openScraperDialog = () => {
        scraperQuery.value = form.value.isbn || form.value.title || ''
        scraperVisible.value = true
    }

    const handleScrapeResult = ({ result, replaceCover }) => {
        if (result.title) form.value.title = result.title
        if (result.isbn) form.value.isbn = result.isbn
        if (result.pub_date) form.value.pub_date = result.pub_date
        if (result.publisher) form.value.publisher_name = result.publisher
        if (result.douban_id) form.value.douban_id = result.douban_id
        if (result.description) form.value.description = result.description

        if (result.authors && result.authors.length) {
            authorsStr.value = result.authors.join(', ')
        }

        if (replaceCover && result.cover_url) {
            form.value.cover_path = result.cover_url
        }

        ElMessage.success(t('bookDetail.save_success'))
    }

    return {
        fileInput,
        uploadingFile,
        downloadingStatus,
        coverInput,
        saving,
        scraperVisible,
        scraperQuery,
        triggerFileUpload,
        handleFileUpload,
        deleteFileLink,
        downloadFile,
        formatBytes,
        handleCoverClick,
        handleCoverChange,
        openScraperDialog,
        handleScrapeResult
    }
}
