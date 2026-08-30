import React, { useState } from 'react'
import {
  Wrench,
  Play,
  Sparkles,
  CheckCircle2,
  Terminal,
  Code,
  ArrowRight,
  ShieldCheck,
} from 'lucide-react'
import { ToolDefinition } from '../../types/api'
import { useProjectStore } from '../../stores/useProjectStore'
import { api } from '../../api/endpoints'
import { Kbd } from '../../components/ui/Kbd'

interface ToolCardProps {
  tool: ToolDefinition
  onOpenLiveTester: (tool: ToolDefinition) => void
  onReviewCode: (tool: ToolDefinition) => void
}

export const ToolCard: React.FC<ToolCardProps> = ({
  tool,
  onOpenLiveTester,
  onReviewCode,
}) => {
  const { activeProject } = useProjectStore()
  const [isRunningInProject, setIsRunningInProject] = useState(false)
  const [injected, setInjected] = useState(false)

  const handleRunInInvestigation = async () => {
    if (!activeProject || isRunningInProject) return
    setIsRunningInProject(true)

    // Build default params based on target seed
    const params: Record<string, any> = {}
    if (tool.params) {
      Object.keys(tool.params).forEach((key) => {
        params[key] = activeProject.target_seed
      })
    }

    try {
      await api.injectTask(
        activeProject.id,
        tool.name,
        params,
        `Analyst triggered tool '${tool.name}' directly from Arsenal`
      )
      setInjected(true)
      setTimeout(() => setInjected(false), 3000)
    } catch (err) {
      console.error('Failed to inject tool task:', err)
    } finally {
      setIsRunningInProject(false)
    }
  }

  return (
    <div className="p-3.5 rounded-lg border border-border-subtle bg-bg-surface hover:border-border-strong transition-all duration-120 flex flex-col justify-between shadow-sm group">
      <div>
        {/* Card Header */}
        <div className="flex items-start justify-between gap-2 mb-2">
          <div className="flex items-center gap-2 min-w-0">
            <div className="w-7 h-7 rounded bg-accent-subtle flex items-center justify-center text-accent shrink-0">
              <Wrench className="w-3.5 h-3.5" strokeWidth={1.5} />
            </div>
            <div className="min-w-0">
              <h4 className="text-xs font-bold text-text-primary font-mono-data truncate">
                {tool.name}
              </h4>
              {tool.category && (
                <span className="text-[10px] text-text-tertiary uppercase tracking-wider">
                  {tool.category}
                </span>
              )}
            </div>
          </div>

          {tool.is_dynamic && (
            <span className="flex items-center gap-1 text-[10px] font-semibold text-accent bg-accent-subtle border border-accent/20 px-1.5 py-0.5 rounded shrink-0">
              <Sparkles className="w-2.5 h-2.5" /> AI-Synthesized
            </span>
          )}
        </div>

        {/* Description */}
        <p className="text-2xs text-text-secondary line-clamp-2 leading-relaxed mb-3">
          {tool.description}
        </p>
      </div>

      {/* Action Footer */}
      <div className="pt-2 border-t border-border-subtle flex items-center justify-between gap-2">
        <div className="flex items-center gap-1">
          {tool.source_code && (
            <button
              onClick={() => onReviewCode(tool)}
              className="p-1 text-text-tertiary hover:text-text-primary hover:bg-bg-canvas rounded transition-colors text-[11px] flex items-center gap-1"
              title="Review AST & Code"
            >
              <Code className="w-3 h-3" /> Code
            </button>
          )}
          <button
            onClick={() => onOpenLiveTester(tool)}
            className="p-1 text-text-tertiary hover:text-text-primary hover:bg-bg-canvas rounded transition-colors text-[11px] flex items-center gap-1"
            title="Open isolated tester"
          >
            <Terminal className="w-3 h-3" /> Test
          </button>
        </div>

        {activeProject && (
          <button
            onClick={handleRunInInvestigation}
            disabled={isRunningInProject || injected}
            className="flex items-center gap-1 px-2.5 py-1 text-2xs font-medium text-white bg-accent hover:bg-accent-hover rounded disabled:opacity-50 transition-colors shrink-0"
          >
            {injected ? (
              <>
                <CheckCircle2 className="w-3 h-3 text-white" /> Injected
              </>
            ) : (
              <>
                <Play className="w-3 h-3" /> Run in Project
              </>
            )}
          </button>
        )}
      </div>
    </div>
  )
}
