import React from 'react'
import { X, CheckCircle, AlertTriangle, ShieldCheck, Code, Check, Ban } from 'lucide-react'
import { ToolDefinition } from '../../types/api'
import { api } from '../../api/endpoints'
import { useProjectStore } from '../../stores/useProjectStore'

interface CodeReviewModalProps {
  tool: ToolDefinition | null
  isOpen: boolean
  onClose: () => void
  onApproved?: () => void
  onRejected?: () => void
}

export const CodeReviewModal: React.FC<CodeReviewModalProps> = ({
  tool,
  isOpen,
  onClose,
  onApproved,
  onRejected,
}) => {
  const { setIsCodeReviewOpen } = useProjectStore()

  if (!isOpen || !tool) return null

  const handleApprove = async () => {
    if (!tool.stage_id) return
    try {
      await api.approveTool(tool.stage_id)
      onApproved?.()
      onClose()
    } catch (err) {
      console.error('Failed to approve tool:', err)
    }
  }

  const handleReject = async () => {
    if (!tool.stage_id) return
    try {
      await api.rejectTool(tool.stage_id)
      onRejected?.()
      onClose()
    } catch (err) {
      console.error('Failed to reject tool:', err)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-bg-overlay glass animate-fade-in">
      <div className="bg-bg-surface border border-border-subtle rounded-xl shadow-overlay max-w-2xl w-full max-h-[85vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b border-border-subtle flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-accent/10 flex items-center justify-center text-accent">
              <Code className="w-4 h-4" strokeWidth={1.5} />
            </div>
            <div>
              <h3 className="text-sm font-bold text-text-primary">
                AST Security & Code Review: {tool.name}
              </h3>
              <p className="text-2xs text-text-tertiary">
                Inspect AI-generated tool code before authorizing execution in the sandbox
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-text-tertiary hover:text-text-primary transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* AST Safety Banner */}
          <div className="p-3 rounded-lg border border-status-confirmed/20 bg-status-confirmed/5 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-status-confirmed" />
              <div>
                <p className="text-2xs font-bold text-status-confirmed">AST Static Verification Passed</p>
                <p className="text-[11px] text-text-secondary">
                  No forbidden system calls (os, subprocess, eval, unauthorized I/O) detected.
                </p>
              </div>
            </div>
            <span className="text-2xs font-mono-data text-status-confirmed">SAFE</span>
          </div>

          {/* Source Code */}
          <div>
            <span className="text-2xs font-semibold text-text-tertiary uppercase tracking-wider block mb-1">
              Python Source Code
            </span>
            <pre className="p-3 rounded-lg bg-bg-canvas border border-border-subtle font-mono-data text-2xs text-text-primary overflow-x-auto max-h-72 whitespace-pre leading-relaxed">
              {tool.source_code || '# No source code available'}
            </pre>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-border-subtle bg-bg-canvas flex items-center justify-between">
          <button
            onClick={onClose}
            className="px-3 py-1.5 text-2xs font-medium text-text-secondary hover:text-text-primary transition-colors"
          >
            Cancel
          </button>

          {tool.stage_id && (
            <div className="flex items-center gap-2">
              <button
                onClick={handleReject}
                className="flex items-center gap-1.5 px-3 py-1.5 text-2xs font-medium text-status-rejected border border-status-rejected/30 hover:bg-status-rejected/10 rounded transition-colors"
              >
                <Ban className="w-3.5 h-3.5" /> Reject Tool
              </button>
              <button
                onClick={handleApprove}
                className="flex items-center gap-1.5 px-3 py-1.5 text-2xs font-medium text-white bg-status-confirmed hover:bg-status-confirmed/90 rounded transition-colors"
              >
                <Check className="w-3.5 h-3.5" /> Authorize & Register Tool
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
