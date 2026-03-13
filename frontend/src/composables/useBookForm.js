import { ref } from 'vue'
import request from '@/utils/request'
import { ElMessage } from 'element-plus'

export function useBookForm({ bookData, localEditMode, visible, t, emit }) {
    const form = ref({
        title: '',
        isbn: '',
        douban_id: '',
        description: '',
        pub_date: '',
        publisher_name: '',
        physical_location: '',
        read_status: '',
        rating: 0,
        cover_path: '',
        custom_code: ''
    })

    const authorsStr = ref('')
    const bookTypeArray = ref([])
    const saving = ref(false)

    const initForm = (newBook) => {
        if (newBook) {
            bookData.value = JSON.parse(JSON.stringify(newBook))

            form.value.title = newBook.title || ''
            form.value.isbn = newBook.isbn || ''
            form.value.douban_id = newBook.douban_id || ''
            form.value.description = newBook.description || ''
            form.value.pub_date = newBook.pub_date || ''
            form.value.publisher_name = newBook.publisher?.name || ''
            form.value.physical_location = newBook.physical_location || ''
            form.value.read_status = newBook.read_status || ''
            form.value.rating = newBook.rating || 0
            form.value.cover_path = newBook.cover_path || ''
            form.value.custom_code = newBook.custom_code || ''

            authorsStr.value = (newBook.authors || []).map(a => a.name).join(', ')
            bookTypeArray.value = newBook.book_type ? newBook.book_type.split(',').map(s => s.trim()) : ['ebook']
        } else {
            bookData.value = null
        }
    }

    const getUpdatePayload = () => {
        return {
            ...form.value,
            book_type: bookTypeArray.value.join(','),
            author_names: authorsStr.value.split(',').map(s => s.trim()).filter(Boolean)
        }
    }

    const autoSaveField = async (fieldFriendlyName) => {
        if (!bookData.value?.id) return
        try {
            await request.put(`/books/${bookData.value.id}`, getUpdatePayload())
            ElMessage.success({ message: t('bookDetail.auto_saved'), duration: 1500 })
            emit('updated')
        } catch (error) {
            console.error(error)
        }
    }

    const handleSave = async () => {
        if (!bookData.value?.id) return
        saving.value = true
        try {
            const res = await request.put(`/books/${bookData.value.id}`, getUpdatePayload())
            ElMessage.success(t('bookDetail.save_success'))

            // Update bookData immediately to reflect new state after save
            if (res && res.id) {
                initForm(res)
            }

            emit('updated')

            if (localEditMode.value) {
                localEditMode.value = false
            } else {
                visible.value = false
            }
        } catch (error) {
            ElMessage.error(error.response?.data?.detail || t('bookDetail.save_failed', '保存失败'))
        } finally {
            saving.value = false
        }
    }

    const handleCancel = () => {
        if (localEditMode.value) {
            localEditMode.value = false
            initForm(bookData.value)
        } else {
            visible.value = false
        }
    }

    return {
        form,
        authorsStr,
        bookTypeArray,
        saving,
        initForm,
        autoSaveField,
        handleSave,
        handleCancel
    }
}
