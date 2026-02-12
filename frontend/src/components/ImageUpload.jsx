import { useCallback, useEffect, useRef } from 'react'
import { SearchIcon, UploadIcon, TrashIcon } from './Icons'

function ImageUpload({ previewUrl, loading, onImageSelected, onSearch, onClear }) {
    const fileInputRef = useRef(null)
    const dropZoneRef = useRef(null)

    const processFile = useCallback((file) => {
        if (!file || !file.type.startsWith('image/')) return
        const reader = new FileReader()
        reader.onload = (e) => {
            onImageSelected(file, e.target.result)
        }
        reader.readAsDataURL(file)
    }, [onImageSelected])

    // Clipboard paste handler
    useEffect(() => {
        const handlePaste = (e) => {
            const items = e.clipboardData?.items
            if (!items) return
            for (const item of items) {
                if (item.type.startsWith('image/')) {
                    e.preventDefault()
                    const file = item.getAsFile()
                    processFile(file)
                    break
                }
            }
        }
        document.addEventListener('paste', handlePaste)
        return () => document.removeEventListener('paste', handlePaste)
    }, [processFile])

    const handleDragOver = useCallback((e) => {
        e.preventDefault()
        e.currentTarget.classList.add('drag-over')
    }, [])

    const handleDragLeave = useCallback((e) => {
        e.preventDefault()
        e.currentTarget.classList.remove('drag-over')
    }, [])

    const handleDrop = useCallback((e) => {
        e.preventDefault()
        e.currentTarget.classList.remove('drag-over')
        const file = e.dataTransfer.files[0]
        processFile(file)
    }, [processFile])

    const handleFileChange = useCallback((e) => {
        const file = e.target.files[0]
        processFile(file)
        e.target.value = ''
    }, [processFile])

    if (previewUrl) {
        return (
            <div className="upload-section">
                <div className="preview-row">
                    <img src={previewUrl} alt="预览" className="preview-image" />
                    <div className="preview-info">
                        <h3>图片已就绪</h3>
                        <p>点击搜索按钮查找相似图片</p>
                    </div>
                    <div className="preview-actions">
                        <button
                            className="btn btn-primary"
                            onClick={onSearch}
                            disabled={loading}
                        >
                            <SearchIcon />
                            {loading ? '搜索中...' : '搜索相似图片'}
                        </button>
                        <button
                            className="btn btn-danger btn-sm"
                            onClick={onClear}
                            disabled={loading}
                        >
                            <TrashIcon />
                            清除
                        </button>
                    </div>
                </div>
            </div>
        )
    }

    return (
        <div className="upload-section">
            <div
                ref={dropZoneRef}
                className="upload-zone"
                onClick={() => fileInputRef.current?.click()}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
            >
                <UploadIcon className="upload-zone-icon" />
                <p className="upload-text">
                    拖拽图片到此处，或点击选择文件
                </p>
                <p className="upload-hint">
                    也可以直接 <kbd>Ctrl</kbd>+<kbd>V</kbd> 粘贴剪贴板中的图片
                </p>
                <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    onChange={handleFileChange}
                    style={{ display: 'none' }}
                />
            </div>
        </div>
    )
}

export default ImageUpload
