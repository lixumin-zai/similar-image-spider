import { memo, useState, useCallback, useRef, useEffect } from 'react'
import { CheckIcon, ZoomInIcon, TrashIcon } from './Icons'

const ImageCard = memo(function ImageCard({ url, index, selected, onPreview, dataIndex }) {
    const [loaded, setLoaded] = useState(false)
    const [error, setError] = useState(false)
    const cardRef = useRef(null)

    useEffect(() => {
        const card = cardRef.current
        if (!card) return
        const observer = new IntersectionObserver(
            ([entry]) => {
                if (entry.isIntersecting) {
                    card.style.animation = 'cardIn 0.3s ease forwards'
                    observer.unobserve(card)
                }
            },
            { threshold: 0.1 }
        )
        observer.observe(card)
        return () => observer.disconnect()
    }, [])

    return (
        <div
            ref={cardRef}
            className={`image-card ${selected ? 'selected' : ''}`}
            data-index={dataIndex}
            style={{ opacity: 0 }}
        >
            {!loaded && !error && (
                <div className="image-placeholder">加载中...</div>
            )}
            {error && (
                <div className="image-placeholder">加载失败</div>
            )}
            <img
                src={url}
                alt={`相似图片 ${index + 1}`}
                loading="lazy"
                draggable={false}
                className={loaded ? 'loaded' : error ? 'error' : ''}
                onLoad={() => setLoaded(true)}
                onError={() => setError(true)}
            />
            <div className="image-overlay">
                <ZoomInIcon className="image-overlay-icon" />
            </div>
            <div className="image-checkbox" title="选择/取消">
                {selected && <CheckIcon />}
            </div>
            <div className="image-index">#{index + 1}</div>
        </div>
    )
})

function ResultsGrid({ results, selectedUrls, onToggleSelect, onBatchSelect, onSelectAll, onDeselectAll, onDeleteSelected, onPreview }) {
    const allSelected = results.length > 0 && selectedUrls.size === results.length
    const gridRef = useRef(null)
    const isDragging = useRef(false)
    const dragStartIndex = useRef(null)
    const dragSelected = useRef(new Set())

    // Resolve data-index from event target
    const getCardIndex = useCallback((el) => {
        const card = el.closest?.('.image-card')
        if (!card) return null
        const idx = card.getAttribute('data-index')
        return idx !== null ? Number(idx) : null
    }, [])

    const handleMouseDown = useCallback((e) => {
        // If clicking checkbox, toggle single selection
        if (e.target.closest('.image-checkbox')) {
            const idx = getCardIndex(e.target)
            if (idx !== null) onToggleSelect(results[idx])
            return
        }

        const idx = getCardIndex(e.target)
        if (idx === null) return

        // Only start drag on left-click
        if (e.button !== 0) return

        isDragging.current = true
        dragStartIndex.current = idx
        dragSelected.current = new Set()
        dragSelected.current.add(idx)
        e.preventDefault()
    }, [getCardIndex, onToggleSelect, results])

    const handleMouseMove = useCallback((e) => {
        if (!isDragging.current) return
        const idx = getCardIndex(e.target)
        if (idx === null) return

        // Select range from dragStart to current
        const start = Math.min(dragStartIndex.current, idx)
        const end = Math.max(dragStartIndex.current, idx)
        const newSet = new Set()
        for (let i = start; i <= end; i++) {
            newSet.add(i)
        }
        dragSelected.current = newSet
        // Live visual: apply via batch
        onBatchSelect(newSet, results)
    }, [getCardIndex, onBatchSelect, results])

    const handleMouseUp = useCallback((e) => {
        if (!isDragging.current) return

        // If didn't actually drag (single click - not on checkbox), open preview
        if (dragSelected.current.size <= 1 && !e.target.closest('.image-checkbox')) {
            const idx = getCardIndex(e.target)
            if (idx !== null && dragSelected.current.size === 1) {
                onPreview(idx)
                // Undo the single selection from drag
                onBatchSelect(new Set(), results)
            }
        }

        isDragging.current = false
        dragStartIndex.current = null
        dragSelected.current = new Set()
    }, [getCardIndex, onPreview, onBatchSelect, results])

    // Cleanup on unmount
    useEffect(() => {
        const handleGlobalUp = () => {
            isDragging.current = false
            dragStartIndex.current = null
            dragSelected.current = new Set()
        }
        window.addEventListener('mouseup', handleGlobalUp)
        return () => window.removeEventListener('mouseup', handleGlobalUp)
    }, [])

    return (
        <div>
            <div className="results-header">
                <span className="results-count">
                    共 <strong>{results.length}</strong> 张相似图片
                    {selectedUrls.size > 0 && (
                        <span> · 已选 <strong>{selectedUrls.size}</strong> 张</span>
                    )}
                </span>
                <div className="results-actions">
                    <button
                        className="btn btn-secondary btn-sm"
                        onClick={allSelected ? onDeselectAll : onSelectAll}
                    >
                        {allSelected ? '取消全选' : '全选'}
                    </button>
                    {selectedUrls.size > 0 && (
                        <>
                            <button
                                className="btn btn-secondary btn-sm"
                                onClick={onDeselectAll}
                            >
                                清除选择
                            </button>
                            <button
                                className="btn btn-danger btn-sm"
                                onClick={onDeleteSelected}
                                title="从结果中移除选中的图片"
                            >
                                <TrashIcon /> 删除选中
                            </button>
                        </>
                    )}
                </div>
            </div>

            <div
                ref={gridRef}
                className="image-grid"
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
            >
                {results.map((url, i) => (
                    <ImageCard
                        key={url}
                        url={url}
                        index={i}
                        dataIndex={i}
                        selected={selectedUrls.has(url)}
                        onPreview={onPreview}
                    />
                ))}
            </div>
        </div>
    )
}

export default ResultsGrid
