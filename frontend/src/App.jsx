import { useState, useCallback, useEffect } from 'react'
import ImageUpload from './components/ImageUpload'
import ResultsGrid from './components/ResultsGrid'
import DownloadBar from './components/DownloadBar'
import ImageModal from './components/ImageModal'
import Toast from './components/Toast'
import { SearchIcon, AlertCircleIcon, InboxIcon } from './components/Icons'
import axios from 'axios'

function App() {
    const [previewUrl, setPreviewUrl] = useState(null)
    const [imageFile, setImageFile] = useState(null)
    const [results, setResults] = useState([])
    const [selectedUrls, setSelectedUrls] = useState(new Set())
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState(null)
    const [toast, setToast] = useState(null)
    const [modalIndex, setModalIndex] = useState(null)

    const showToast = useCallback((message, type = 'success') => {
        setToast({ message, type })
        setTimeout(() => setToast(null), 3000)
    }, [])

    const handleImageSelected = useCallback((file, preview) => {
        setImageFile(file)
        setPreviewUrl(preview)
        setResults([])
        setSelectedUrls(new Set())
        setError(null)
    }, [])

    const handleSearch = useCallback(async () => {
        if (!imageFile) return

        setLoading(true)
        setError(null)
        setResults([])
        setSelectedUrls(new Set())

        try {
            const formData = new FormData()
            formData.append('file', imageFile)

            const response = await axios.post('/search-similar', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
                timeout: 120000,
            })

            if (response.data.success) {
                setResults(response.data.data.images_url)
                showToast(`找到 ${response.data.data.total_count} 张相似图片`)
            } else {
                setError(response.data.message || '搜索失败')
            }
        } catch (err) {
            const msg = err.response?.data?.detail || err.message || '搜索请求失败'
            setError(msg)
        } finally {
            setLoading(false)
        }
    }, [imageFile, showToast])

    const handleToggleSelect = useCallback((url) => {
        setSelectedUrls(prev => {
            const next = new Set(prev)
            if (next.has(url)) {
                next.delete(url)
            } else {
                next.add(url)
            }
            return next
        })
    }, [])

    // Batch select by index set (used by drag-to-select)
    const handleBatchSelect = useCallback((indexSet, resultsList) => {
        setSelectedUrls(prev => {
            const next = new Set(prev)
            for (const idx of indexSet) {
                if (resultsList[idx]) {
                    next.add(resultsList[idx])
                }
            }
            return next
        })
    }, [])

    const handleSelectAll = useCallback(() => {
        setSelectedUrls(new Set(results))
    }, [results])

    const handleDeselectAll = useCallback(() => {
        setSelectedUrls(new Set())
    }, [])

    // Delete selected images from results
    const handleDeleteSelected = useCallback(() => {
        if (selectedUrls.size === 0) return
        const count = selectedUrls.size
        setResults(prev => prev.filter(url => !selectedUrls.has(url)))
        setSelectedUrls(new Set())
        setModalIndex(null)
        showToast(`已移除 ${count} 张图片`)
    }, [selectedUrls, showToast])

    const handleClear = useCallback(() => {
        setPreviewUrl(null)
        setImageFile(null)
        setResults([])
        setSelectedUrls(new Set())
        setError(null)
    }, [])

    const handlePreview = useCallback((index) => {
        setModalIndex(index)
    }, [])

    const handleModalPrev = useCallback(() => {
        setModalIndex(prev => (prev > 0 ? prev - 1 : prev))
    }, [])

    const handleModalNext = useCallback(() => {
        setModalIndex(prev => (prev < results.length - 1 ? prev + 1 : prev))
    }, [results.length])

    return (
        <div className="app">
            <header className="header">
                <div className="header-icon">
                    <SearchIcon />
                </div>
                <h1>Similar Image Spider</h1>
                <span className="header-subtitle">Upload · Search · Download</span>
            </header>

            <main className="main-content">
                <ImageUpload
                    previewUrl={previewUrl}
                    loading={loading}
                    onImageSelected={handleImageSelected}
                    onSearch={handleSearch}
                    onClear={handleClear}
                />

                {loading && (
                    <div className="loading-container">
                        <div className="spinner" />
                        <p className="loading-text">正在搜索相似图片，请稍候...</p>
                    </div>
                )}

                {error && (
                    <div className="error-container">
                        <p><AlertCircleIcon style={{ width: 18, height: 18 }} /> {error}</p>
                        <button className="btn btn-secondary btn-sm" onClick={() => setError(null)}>
                            关闭
                        </button>
                    </div>
                )}

                {!loading && !error && results.length > 0 && (
                    <ResultsGrid
                        results={results}
                        selectedUrls={selectedUrls}
                        onToggleSelect={handleToggleSelect}
                        onBatchSelect={handleBatchSelect}
                        onSelectAll={handleSelectAll}
                        onDeselectAll={handleDeselectAll}
                        onDeleteSelected={handleDeleteSelected}
                        onPreview={handlePreview}
                    />
                )}

                {!loading && !error && results.length === 0 && previewUrl && !imageFile && (
                    <div className="empty-state">
                        <InboxIcon className="empty-state-icon" />
                        <h3>暂无搜索结果</h3>
                    </div>
                )}
            </main>

            {selectedUrls.size > 0 && (
                <DownloadBar
                    selectedUrls={selectedUrls}
                    totalCount={results.length}
                    onDeselectAll={handleDeselectAll}
                    onDeleteSelected={handleDeleteSelected}
                    onToast={showToast}
                />
            )}

            {modalIndex !== null && results[modalIndex] && (
                <ImageModal
                    url={results[modalIndex]}
                    index={modalIndex}
                    total={results.length}
                    onClose={() => setModalIndex(null)}
                    onPrev={modalIndex > 0 ? handleModalPrev : null}
                    onNext={modalIndex < results.length - 1 ? handleModalNext : null}
                />
            )}

            {toast && <Toast message={toast.message} type={toast.type} />}
        </div>
    )
}

export default App
