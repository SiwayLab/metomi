import { ref, nextTick } from 'vue'
import { ElMessage } from 'element-plus'

export function usePdfReader(options) {
    const {
        readerMain,
        currentPage,
        totalPages,
        tocItems,
        loading,
        t
    } = options

    const pdfPageRefs = {}
    const pdfCanvasRefs = {}
    let pdfDoc = null
    let pdfObserver = null

    const renderedPages = {}
    const renderingPages = {}
    const pageVisibility = {}
    const RENDER_BUFFER = 5
    const MAX_RENDER_CONCURRENCY = 2
    const MAX_DPR = 1.5
    const MAX_SCALE = 2.0

    const renderQueue = []
    const queuedPages = new Map()
    let activeRenderCount = 0

    const getRenderPriority = (center, page) => {
        const dist = Math.abs(page - center)
        if (dist === 0) return 2
        if (dist <= 1) return 1
        return 0
    }

    const enqueueRender = (pageNum, priority = 0) => {
        if (!pdfDoc || renderedPages[pageNum] || renderingPages[pageNum]) return
        if (queuedPages.has(pageNum)) {
            const existingPriority = queuedPages.get(pageNum)
            if (priority > existingPriority) {
                queuedPages.set(pageNum, priority)
                const item = renderQueue.find((entry) => entry.pageNum === pageNum)
                if (item) item.priority = priority
            }
            return
        }
        queuedPages.set(pageNum, priority)
        renderQueue.push({ pageNum, priority })
        processRenderQueue()
    }

    const processRenderQueue = () => {
        if (activeRenderCount >= MAX_RENDER_CONCURRENCY) return
        if (!renderQueue.length) return
        renderQueue.sort((a, b) => {
            if (b.priority !== a.priority) return b.priority - a.priority
            return Math.abs(a.pageNum - currentPage.value) - Math.abs(b.pageNum - currentPage.value)
        })
        while (activeRenderCount < MAX_RENDER_CONCURRENCY && renderQueue.length) {
            const task = renderQueue.shift()
            if (!task) break
            queuedPages.delete(task.pageNum)
            activeRenderCount += 1
            renderPage(task.pageNum)
                .catch(() => { /* handled in renderPage */ })
                .finally(() => {
                    activeRenderCount = Math.max(0, activeRenderCount - 1)
                    processRenderQueue()
                })
        }
    }

    const setPdfPageRef = (el, page) => {
        if (el) pdfPageRefs[page] = el
    }

    const setPdfCanvasRef = (el, page) => {
        if (el) pdfCanvasRefs[page] = el
    }

    const initPdf = async (streamUrl) => {
        try {
            const pdfjsLib = await import('pdfjs-dist')
            pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
                'pdfjs-dist/build/pdf.worker.js',
                import.meta.url
            ).href

            // Fix 28: PDF.js 载入开启 withCredentials 以携带 httpOnly cookie
            const loadingTask = pdfjsLib.getDocument({
                url: streamUrl,
                withCredentials: true,
                rangeChunkSize: 65536,
                disableAutoFetch: false,
                disableStream: false,
            })
            pdfDoc = await loadingTask.promise
            totalPages.value = pdfDoc.numPages

            const initialPage = Math.min(
                Math.max(parseInt(currentPage.value) || 1, 1),
                pdfDoc.numPages || 1
            )
            currentPage.value = initialPage

            // Sample first page's aspect ratio and apply to all pages as default.
            // Actual ratios are updated lazily in renderPage() when each page renders.
            let defaultRatio = 1 / 1.414 // A4 fallback
            try {
                const firstPage = await pdfDoc.getPage(1)
                const vp = firstPage.getViewport({ scale: 1.0 })
                defaultRatio = vp.width / vp.height
            } catch (e) { /* use A4 fallback */ }

            if (options.pageAspectRatios) {
                const ratios = {}
                for (let i = 1; i <= pdfDoc.numPages; i++) {
                    ratios[i] = defaultRatio
                }
                options.pageAspectRatios.value = ratios
            }

            // Load outline in background (not awaited)
            loadPdfOutline(pdfDoc)

            await nextTick()

            // Prevent observer from overwriting the saved page during initial jump.
            isJumping = currentPage.value > 1

            // Set up observer immediately so pages near viewport start rendering
            setupPdfObserver()

            // Jump to saved position if needed
            if (currentPage.value > 1) {
                await scrollToPdfPage(currentPage.value, 'instant')
                setTimeout(() => { isJumping = false }, 150)
            } else {
                isJumping = false
            }

            loading.value = false
        } catch (e) {
            console.error('PDF Load Error:', e)
            ElMessage.error(t('reader.pdf_load_error'))
            loading.value = false
        }
    }

    const renderPage = async (pageNum) => {
        if (!pdfDoc || renderedPages[pageNum] || renderingPages[pageNum]) return
        const canvas = pdfCanvasRefs[pageNum]
        if (!canvas) return

        renderingPages[pageNum] = true
        try {
            const page = await pdfDoc.getPage(pageNum)
            const baseViewport = page.getViewport({ scale: 1.0 })
            let targetWidth = 0
            const wrapper = pdfPageRefs[pageNum]
            if (wrapper) targetWidth = wrapper.clientWidth
            if (!targetWidth && readerMain.value) targetWidth = readerMain.value.clientWidth
            if (!targetWidth) targetWidth = baseViewport.width
            const dpr = Math.min(window.devicePixelRatio || 1, MAX_DPR)
            const scale = Math.min(MAX_SCALE, Math.max(0.75, (targetWidth / baseViewport.width) * dpr))
            const viewport = page.getViewport({ scale })

            // Lazily update actual aspect ratio for this page
            if (options.pageAspectRatios) {
                const realRatio = baseViewport.width / baseViewport.height
                if (Math.abs((options.pageAspectRatios.value[pageNum] || 0) - realRatio) > 0.001) {
                    options.pageAspectRatios.value[pageNum] = realRatio
                }
            }

            canvas.width = viewport.width
            canvas.height = viewport.height
            canvas.style.width = '100%'
            canvas.style.height = 'auto'

            const ctx = canvas.getContext('2d')
            await page.render({ canvasContext: ctx, viewport }).promise

            renderedPages[pageNum] = true
        } catch (e) {
            console.warn(`渲染第 ${pageNum} 页失败:`, e)
        } finally {
            delete renderingPages[pageNum]
        }
    }

    const clearPage = (pageNum) => {
        if (!renderedPages[pageNum]) return
        const canvas = pdfCanvasRefs[pageNum]
        if (canvas) {
            const ctx = canvas.getContext('2d')
            ctx.clearRect(0, 0, canvas.width, canvas.height)
        }
        delete renderedPages[pageNum]
    }

    const setupPdfObserver = () => {
        if (!readerMain.value) return
        pdfObserver = new IntersectionObserver(
            (entries) => {
                for (const entry of entries) {
                    const page = parseInt(entry.target.dataset.page)
                    if (entry.isIntersecting) {
                        pageVisibility[page] = entry.intersectionRatio
                        enqueueRender(page, 2)
                    } else {
                        delete pageVisibility[page]
                    }
                }
                let bestPage = currentPage.value
                let bestRatio = 0
                for (const [p, ratio] of Object.entries(pageVisibility)) {
                    if (ratio > bestRatio) {
                        bestRatio = ratio
                        bestPage = parseInt(p)
                    }
                }
                if (bestPage !== currentPage.value && bestRatio > 0 && !isJumping) {
                    currentPage.value = bestPage
                }
                const center = currentPage.value
                const start = Math.max(1, center - RENDER_BUFFER)
                const end = Math.min(totalPages.value, center + RENDER_BUFFER)
                for (let i = start; i <= end; i++) {
                    enqueueRender(i, getRenderPriority(center, i))
                }
                if (!isJumping) {
                    for (const p in renderedPages) {
                        const pn = parseInt(p)
                        if (pn < center - RENDER_BUFFER * 2 || pn > center + RENDER_BUFFER * 2) {
                            clearPage(pn)
                        }
                    }
                }
            },
            {
                root: readerMain.value,
                rootMargin: '100% 0px',
                threshold: [0, 0.25, 0.5, 0.75, 1.0],
            }
        )

        for (const page in pdfPageRefs) {
            pdfObserver.observe(pdfPageRefs[page])
        }
    }

    const scrollToPdfPage = async (page, behavior = 'smooth') => {
        await nextTick()
        const el = pdfPageRefs[page]
        if (el) el.scrollIntoView({ behavior, block: 'start' })
        const start = Math.max(1, page - RENDER_BUFFER)
        const end = Math.min(totalPages.value, page + RENDER_BUFFER)
        for (let i = start; i <= end; i++) {
            enqueueRender(i, getRenderPriority(page, i))
        }
    }

    let isJumping = false

    const jumpToPage = async (page, saveHook) => {
        if (page < 1 || page > totalPages.value) return
        isJumping = true
        currentPage.value = page
        await scrollToPdfPage(page)
        // Allow observer to settle after scroll animation
        setTimeout(() => { isJumping = false }, 600)
        if (saveHook) saveHook()
    }

    const loadPdfOutline = async (doc) => {
        try {
            const outline = await doc.getOutline()
            if (!outline || !outline.length) return

            const items = []
            const flatten = async (list, level) => {
                for (const entry of list) {
                    let pageNum = null
                    if (entry.dest) {
                        try {
                            const dest = typeof entry.dest === 'string'
                                ? await doc.getDestination(entry.dest)
                                : entry.dest
                            if (dest && dest[0]) {
                                const pageIdx = await doc.getPageIndex(dest[0])
                                pageNum = pageIdx + 1
                            }
                        } catch (e) { /* ignore */ }
                    }
                    items.push({ label: entry.title, level, page: pageNum, type: 'pdf' })
                    if (entry.items && entry.items.length) {
                        await flatten(entry.items, level + 1)
                    }
                }
            }
            await flatten(outline, 0)
            tocItems.value = items
        } catch (e) {
            console.warn('Failed to load PDF outline:', e)
        }
    }

    const destroyPdf = () => {
        if (pdfObserver) {
            pdfObserver.disconnect()
            pdfObserver = null
        }
        renderQueue.length = 0
        queuedPages.clear()
        if (pdfDoc) {
            try { pdfDoc.destroy() } catch (e) { /* ignore */ }
            pdfDoc = null
        }
    }

    return {
        initPdf,
        setPdfPageRef,
        setPdfCanvasRef,
        jumpToPage,
        destroyPdf
    }
}
