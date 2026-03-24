import { useState, useCallback } from 'react'
import { DownloadIcon, TrashIcon, FileTextIcon } from './Icons'
import axios from 'axios'

function DownloadBar({ selectedUrls, totalCount, onDeselectAll, onDeleteSelected, onToast }) {
    const [downloading, setDownloading] = useState(false)

    const handleDownloadUrls = useCallback(() => {
        if (selectedUrls.size === 0) return
        
        const urlsText = Array.from(selectedUrls).join('\n')
        const blob = new Blob([urlsText], { type: 'text/plain' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = 'url.txt'
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
        
        onToast(`成功导出 ${selectedUrls.size} 个URL`, 'success')
    }, [selectedUrls, onToast])

    const handleDownload = useCallback(async () => {
        if (downloading || selectedUrls.size === 0) return

        setDownloading(true)
        try {
            const response = await axios.post(
                '/download-images',
                { urls: Array.from(selectedUrls) },
                {
                    responseType: 'blob',
                    timeout: 300000,
                }
            )

            const blob = new Blob([response.data], { type: 'application/zip' })
            const url = URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = `similar_images_${Date.now()}.zip`
            document.body.appendChild(a)
            a.click()
            document.body.removeChild(a)
            URL.revokeObjectURL(url)

            onToast(`成功下载 ${selectedUrls.size} 张图片`, 'success')
        } catch (err) {
            const msg = err.response?.data?.detail || '下载失败，请重试'
            onToast(msg, 'error')
        } finally {
            setDownloading(false)
        }
    }, [selectedUrls, downloading, onToast])

    return (
        <div className="download-bar">
            <span className="selected-count">
                已选择 <strong>{selectedUrls.size}</strong> / {totalCount} 张图片
            </span>

            {downloading ? (
                <div className="download-progress">
                    <div className="spinner" />
                    <span>正在打包下载中...</span>
                </div>
            ) : (
                <>
                    <button className="btn btn-primary" onClick={handleDownload}>
                        <DownloadIcon />
                        下载选中
                    </button>
                    <button className="btn btn-secondary" onClick={handleDownloadUrls}>
                        <FileTextIcon />
                        获取URL
                    </button>
                    <button className="btn btn-danger btn-sm" onClick={onDeleteSelected}>
                        <TrashIcon />
                        删除选中
                    </button>
                    <button className="btn btn-secondary btn-sm" onClick={onDeselectAll}>
                        取消选择
                    </button>
                </>
            )}
        </div>
    )
}

export default DownloadBar
