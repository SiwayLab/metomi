import { ref, nextTick } from 'vue'
import { ElMessage } from 'element-plus'

export function useEpubReader(options) {
    const {
        epubContainer,
        tocItems,
        loading,
        t
    } = options

    let epubBook = null
    let epubRendition = null
    let currentEpubCfi = ''
    let epubLocations = null
    let lastEpubLocation = null

    const epubLocationLabel = ref('')

    const updateEpubLabel = () => {
        const parts = []
        // Removed literal page numbers as per user preference
        if (epubLocations && epubBook && epubBook.locations && currentEpubCfi) {
            try {
                const pct = epubBook.locations.percentageFromCfi(currentEpubCfi)
                if (typeof pct === 'number' && !isNaN(pct)) {
                    parts.push(`${t('reader.progress')} ${Math.round(pct * 100)}%`)
                }
            } catch (e) {
                console.warn('percentageFromCfi error:', e)
            }
        }
        epubLocationLabel.value = parts.length ? parts.join(' · ') : t('reader.epub_reading')
    }

    const initEpub = async (streamUrl, savedCfi) => {
        await nextTick()
        try {
            console.log("EPUB Init: Starting ePub library import...")
            const ePub = (await import('epubjs')).default

            console.log("EPUB Init: Fetching EPUB as ArrayBuffer from:", streamUrl)
            const response = await fetch(streamUrl, {
                credentials: 'include'
            })
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`)
            }
            const buffer = await response.arrayBuffer()

            console.log("EPUB Init: Buffer received, initializing ePub...")
            epubBook = ePub(buffer)

            console.log("EPUB Init: Awaiting book.ready...")
            await epubBook.ready
            console.log("EPUB Init: book.ready resolved.")

            epubRendition = epubBook.renderTo(epubContainer.value, {
                width: '100%',
                height: '100%',
                spread: 'none',
            })

            console.log("EPUB Init: Awaiting rendition.display(). savedCfi=", savedCfi)
            if (savedCfi) {
                await epubRendition.display(savedCfi)
            } else {
                await epubRendition.display()
            }
            console.log("EPUB Init: rendition.display() finished.")

            epubBook.locations.generate(1600).then(() => {
                epubLocations = true
                updateEpubLabel()
            }).catch(() => { })

            epubRendition.on('relocated', (location) => {
                if (location && location.start && location.start.cfi) {
                    currentEpubCfi = location.start.cfi
                }
                lastEpubLocation = location
                updateEpubLabel()
            })

            epubRendition.hooks.content.register((contents) => {
                const doc = contents.document
                doc.addEventListener('mousedown', (e) => {
                    const width = doc.documentElement.clientWidth
                    const x = e.clientX
                    if (x < width * 0.2 || x > width * 0.8) {
                        e.preventDefault()
                    }
                })
                doc.addEventListener('mouseup', (e) => {
                    const width = doc.documentElement.clientWidth
                    const x = e.clientX
                    if (x < width * 0.2) epubPrev()
                    else if (x > width * 0.8) epubNext()
                })
            })

            console.log("EPUB Init: Loading TOC...")
            loadEpubToc()
            loading.value = false
            console.log("EPUB Init: Success! loading=false.")
        } catch (err) {
            loading.value = false
            ElMessage.error(t('reader.epub_load_error'))
            console.error('EPUB load error:', err)
        }
    }

    const loadEpubToc = () => {
        if (!epubBook || !epubBook.navigation) return
        try {
            const items = []
            const flatten = (list, level) => {
                for (const item of list) {
                    items.push({ label: item.label, href: item.href, level, type: 'epub' })
                    if (item.subitems && item.subitems.length) {
                        flatten(item.subitems, level + 1)
                    }
                }
            }
            flatten(epubBook.navigation.toc, 0)
            tocItems.value = items
        } catch (e) {
            console.warn('Failed to load EPUB TOC:', e)
        }
    }

    const epubPrev = () => {
        if (epubRendition) epubRendition.prev()
    }

    const epubNext = () => {
        if (epubRendition) epubRendition.next()
    }

    const jumpToEpubHref = (href) => {
        if (epubRendition && href) epubRendition.display(href)
    }

    const getEpubCfi = () => currentEpubCfi

    const destroyEpub = () => {
        if (epubRendition) {
            try { epubRendition.destroy() } catch (e) { /* ignore */ }
        }
        if (epubBook) {
            try { epubBook.destroy() } catch (e) { /* ignore */ }
        }
    }

    return {
        epubLocationLabel,
        initEpub,
        epubPrev,
        epubNext,
        jumpToEpubHref,
        getEpubCfi,
        destroyEpub
    }
}
