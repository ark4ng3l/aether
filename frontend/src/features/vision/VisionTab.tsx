import React, { useState } from 'react'
import {
  Upload,
  Image as ImageIcon,
  Sparkles,
  MapPin,
  Camera,
  Hash,
  Eye,
  Columns,
  Layers,
  Shield,
  CheckCircle2,
} from 'lucide-react'
import { api } from '../../api/endpoints'
import { EmptyState } from '../../components/ui/EmptyState'

interface AnalyzedImage {
  id: string
  filename: string
  file: File
  previewUrl: string
  status: 'uploading' | 'analyzing' | 'done' | 'failed'
  result?: any
  error?: string
}

export const VisionTab: React.FC = () => {
  const [images, setImages] = useState<AnalyzedImage[]>([])
  const [selectedImageId, setSelectedImageId] = useState<string | null>(null)
  const [compareMode, setCompareMode] = useState(false)
  const [compareSelectedIds, setCompareSelectedIds] = useState<string[]>([])

  const handleFilesSelected = async (files: FileList | null) => {
    if (!files || files.length === 0) return

    const newImages: AnalyzedImage[] = Array.from(files).map((file) => ({
      id: `${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
      filename: file.name,
      file,
      previewUrl: URL.createObjectURL(file),
      status: 'uploading',
    }))

    setImages((prev) => [...prev, ...newImages])
    if (!selectedImageId && newImages.length > 0) {
      setSelectedImageId(newImages[0].id)
    }

    // Process each file
    for (const img of newImages) {
      try {
        const uploadRes = await api.uploadImage(img.file)
        setImages((prev) =>
          prev.map((i) => (i.id === img.id ? { ...i, status: 'analyzing', filename: uploadRes.filename } : i))
        )

        const analysisRes = await api.analyzeImage(uploadRes.filename)
        setImages((prev) =>
          prev.map((i) =>
            i.id === img.id ? { ...i, status: 'done', result: analysisRes.data || analysisRes } : i
          )
        )
      } catch (err: any) {
        setImages((prev) =>
          prev.map((i) => (i.id === img.id ? { ...i, status: 'failed', error: err.message } : i))
        )
      }
    }
  }

  const selectedImage = images.find((i) => i.id === selectedImageId)
  const compareImages = images.filter((i) => compareSelectedIds.includes(i.id))

  const toggleCompareSelect = (id: string) => {
    setCompareSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id].slice(0, 3)
    )
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-bg-canvas select-none">
      {/* Top action bar */}
      <div className="p-3 bg-bg-surface border-b border-border-subtle flex items-center justify-between gap-3 shrink-0">
        <div className="flex items-center gap-2">
          <ImageIcon className="w-4 h-4 text-accent" strokeWidth={1.5} />
          <h3 className="text-xs font-semibold text-text-primary">Vision & Image Forensics</h3>
          <span className="text-2xs text-text-tertiary font-mono-data">({images.length} images)</span>
        </div>

        <div className="flex items-center gap-2">
          {images.length >= 2 && (
            <button
              onClick={() => {
                setCompareMode(!compareMode)
                if (!compareMode && images.length >= 2) {
                  setCompareSelectedIds([images[0].id, images[1].id])
                }
              }}
              className={`flex items-center gap-1.5 px-2.5 py-1 text-2xs font-medium rounded border transition-colors ${
                compareMode
                  ? 'bg-accent text-white border-accent'
                  : 'bg-bg-canvas text-text-secondary border-border-subtle hover:text-text-primary'
              }`}
            >
              <Columns className="w-3 h-3" />
              {compareMode ? 'Exit Compare' : 'Compare EXIF'}
            </button>
          )}

          <label className="flex items-center gap-1.5 px-3 py-1 text-2xs font-medium text-white bg-accent hover:bg-accent-hover rounded cursor-pointer transition-colors">
            <Upload className="w-3 h-3" />
            Upload Image(s)
            <input
              type="file"
              multiple
              accept="image/*"
              className="hidden"
              onChange={(e) => handleFilesSelected(e.target.files)}
            />
          </label>
        </div>
      </div>

      {images.length === 0 ? (
        <div className="flex-1 flex items-center justify-center">
          <label className="cursor-pointer">
            <EmptyState
              icon={Upload}
              title="Upload images for passive forensic analysis"
              description="Extract GPS metadata, EXIF camera tags, perceptual hashes, and OCR text via local Vision LLM."
            />
            <input
              type="file"
              multiple
              accept="image/*"
              className="hidden"
              onChange={(e) => handleFilesSelected(e.target.files)}
            />
          </label>
        </div>
      ) : (
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Filmstrip */}
          <div className="p-3 bg-bg-surface border-b border-border-subtle flex items-center gap-3 overflow-x-auto scrollbar-none shrink-0">
            {images.map((img) => {
              const isSelected = img.id === selectedImageId
              const isCompared = compareSelectedIds.includes(img.id)

              return (
                <div
                  key={img.id}
                  onClick={() => {
                    if (compareMode) {
                      toggleCompareSelect(img.id)
                    } else {
                      setSelectedImageId(img.id)
                    }
                  }}
                  className={`relative group shrink-0 w-20 h-20 rounded-lg overflow-hidden border-2 cursor-pointer transition-all ${
                    compareMode
                      ? isCompared
                        ? 'border-accent ring-2 ring-accent/30'
                        : 'border-border-subtle opacity-60'
                      : isSelected
                      ? 'border-accent shadow-md'
                      : 'border-border-subtle hover:border-border-strong'
                  }`}
                >
                  <img src={img.previewUrl} alt={img.filename} className="w-full h-full object-cover" />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent flex items-end p-1">
                    <span className="text-[9px] text-white font-mono-data truncate w-full">
                      {img.filename}
                    </span>
                  </div>
                  {img.status === 'analyzing' && (
                    <div className="absolute inset-0 bg-black/50 flex items-center justify-center text-[10px] text-white font-medium animate-pulse">
                      Analyzing...
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          {/* Main Inspection View */}
          <div className="flex-1 overflow-y-auto p-4 select-text">
            {compareMode ? (
              /* Compare EXIF Side-by-Side */
              <div className="space-y-4">
                <h4 className="text-xs font-bold text-text-primary flex items-center gap-1.5">
                  <Columns className="w-3.5 h-3.5 text-accent" />
                  Side-by-Side Forensic Metadata Comparison ({compareImages.length} images)
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {compareImages.map((img) => (
                    <div key={img.id} className="p-3.5 rounded-lg border border-border-subtle bg-bg-surface space-y-3">
                      <div className="h-40 rounded overflow-hidden bg-bg-canvas">
                        <img src={img.previewUrl} alt={img.filename} className="w-full h-full object-contain" />
                      </div>
                      <p className="text-xs font-bold text-text-primary font-mono-data truncate">{img.filename}</p>

                      <div className="space-y-1 text-2xs">
                        <div className="p-2 rounded bg-bg-canvas border border-border-subtle space-y-1">
                          <p className="text-text-tertiary uppercase tracking-wider font-semibold text-[10px]">EXIF & Telemetry</p>
                          <p className="text-text-secondary">Camera: <span className="text-text-primary font-mono-data">{img.result?.exif?.Make || 'Unknown'} {img.result?.exif?.Model || ''}</span></p>
                          <p className="text-text-secondary">GPS: <span className="text-text-primary font-mono-data">{img.result?.gps?.latitude ? `${img.result.gps.latitude}, ${img.result.gps.longitude}` : 'No GPS Tags'}</span></p>
                          <p className="text-text-secondary">Date: <span className="text-text-primary font-mono-data">{img.result?.exif?.DateTime || 'Not Stamped'}</span></p>
                          <p className="text-text-secondary">pHash: <span className="text-text-primary font-mono-data text-[10px] break-all">{img.result?.phash || 'N/A'}</span></p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : selectedImage ? (
              /* Single Image Deep View */
              <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
                {/* Left: Image preview */}
                <div className="lg:col-span-2 space-y-3">
                  <div className="rounded-xl border border-border-subtle bg-bg-surface p-2 overflow-hidden shadow-sm">
                    <img
                      src={selectedImage.previewUrl}
                      alt={selectedImage.filename}
                      className="w-full h-auto max-h-96 object-contain rounded-lg"
                    />
                  </div>
                  <div className="p-3 rounded-lg border border-border-subtle bg-bg-surface space-y-1 text-2xs">
                    <p className="text-text-tertiary">Filename: <span className="text-text-primary font-mono-data">{selectedImage.filename}</span></p>
                    <p className="text-text-tertiary">Filesize: <span className="text-text-primary font-mono-data">{(selectedImage.file.size / 1024).toFixed(1)} KB</span></p>
                    <p className="text-text-tertiary">Type: <span className="text-text-primary font-mono-data">{selectedImage.file.type}</span></p>
                  </div>
                </div>

                {/* Right: Extracted Forensic Signals */}
                <div className="lg:col-span-3 space-y-4">
                  {selectedImage.status === 'analyzing' ? (
                    <p className="text-2xs text-text-tertiary py-8 text-center animate-pulse">
                      Running local VLM OCR, perceptual hash computation, and EXIF extraction...
                    </p>
                  ) : selectedImage.result ? (
                    <>
                      {/* GPS Telemetry */}
                      <div className="p-3.5 rounded-lg border border-border-subtle bg-bg-surface space-y-2">
                        <span className="flex items-center gap-1.5 text-2xs font-bold text-accent uppercase tracking-wider">
                          <MapPin className="w-3.5 h-3.5" /> Geolocation Telemetry
                        </span>
                        {selectedImage.result.gps ? (
                          <div className="space-y-1 text-2xs">
                            <p className="text-text-primary font-mono-data">
                              Latitude: {selectedImage.result.gps.latitude}, Longitude: {selectedImage.result.gps.longitude}
                            </p>
                            {selectedImage.result.gps.altitude && (
                              <p className="text-text-secondary font-mono-data">Altitude: {selectedImage.result.gps.altitude}m</p>
                            )}
                          </div>
                        ) : (
                          <p className="text-2xs text-text-tertiary italic">No embedded GPS coordinates found in EXIF data.</p>
                        )}
                      </div>

                      {/* Vision OCR / Scene Description */}
                      <div className="p-3.5 rounded-lg border border-border-subtle bg-bg-surface space-y-2">
                        <span className="flex items-center gap-1.5 text-2xs font-bold text-accent uppercase tracking-wider">
                          <Sparkles className="w-3.5 h-3.5" /> AI Vision & Optical Character Recognition (OCR)
                        </span>
                        <p className="text-2xs text-text-secondary leading-relaxed font-sans">
                          {selectedImage.result.description || selectedImage.result.ocr_text || 'No text or description extracted.'}
                        </p>
                      </div>

                      {/* EXIF Metadata Table */}
                      <div className="p-3.5 rounded-lg border border-border-subtle bg-bg-surface space-y-2">
                        <span className="flex items-center gap-1.5 text-2xs font-bold text-accent uppercase tracking-wider">
                          <Camera className="w-3.5 h-3.5" /> Camera & Hardware Metadata
                        </span>
                        <pre className="p-2.5 rounded bg-bg-canvas border border-border-subtle text-[11px] font-mono-data text-text-secondary max-h-48 overflow-y-auto whitespace-pre-wrap">
                          {JSON.stringify(selectedImage.result.exif || {}, null, 2)}
                        </pre>
                      </div>
                    </>
                  ) : selectedImage.error ? (
                    <div className="p-4 rounded-lg bg-status-rejected/10 border border-status-rejected/20 text-2xs text-status-rejected">
                      Analysis failed: {selectedImage.error}
                    </div>
                  ) : null}
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  )
}
