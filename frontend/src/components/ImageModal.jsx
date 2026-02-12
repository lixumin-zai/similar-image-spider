import { useEffect, useCallback } from 'react'
import { XIcon, ChevronLeftIcon, ChevronRightIcon, ExternalLinkIcon } from './Icons'

function ImageModal({ url, index, total, onClose, onPrev, onNext }) {
    const handleKeyDown = useCallback((e) => {
        if (e.key === 'Escape') onClose()
        if (e.key === 'ArrowLeft') onPrev?.()
        if (e.key === 'ArrowRight') onNext?.()
    }, [onClose, onPrev, onNext])

    useEffect(() => {
        document.addEventListener('keydown', handleKeyDown)
        document.body.style.overflow = 'hidden'
        return () => {
            document.removeEventListener('keydown', handleKeyDown)
            document.body.style.overflow = ''
        }
    }, [handleKeyDown])

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                <img src={url} alt={`图片 ${index + 1}`} className="modal-image" />
                <div className="modal-info">
                    <span>#{index + 1} / {total}</span>
                    <a href={url} target="_blank" rel="noopener noreferrer" className="btn btn-secondary btn-sm">
                        <ExternalLinkIcon /> 新窗口打开
                    </a>
                </div>
            </div>

            {onPrev && (
                <button className="modal-nav modal-nav-prev" onClick={(e) => { e.stopPropagation(); onPrev() }}>
                    <ChevronLeftIcon />
                </button>
            )}
            {onNext && (
                <button className="modal-nav modal-nav-next" onClick={(e) => { e.stopPropagation(); onNext() }}>
                    <ChevronRightIcon />
                </button>
            )}

            <button className="modal-close" onClick={onClose}><XIcon /></button>
        </div>
    )
}

export default ImageModal
