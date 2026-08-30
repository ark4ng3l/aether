import React, { useState, useEffect } from 'react'
import { Sparkles, ArrowRight, CheckCircle2, Play } from 'lucide-react'
import { useProjectStore } from '../../stores/useProjectStore'
import { useTaskStore } from '../../stores/useTaskStore'
import { api } from '../../api/endpoints'

export const NextActionCard: React.FC = () => {
  const { activeProject } = useProjectStore()
  const { activeHypotheses } = useTaskStore()
  const [suggestedTask, setSuggestedTask] = useState<string | null>(null)
  const [isExecuting, setIsExecuting] = useState(false)
  const [executed, setExecuted] = useState(false)

  useEffect(() => {
    if (!activeProject) {
      setSuggestedTask(null)
      return
    }

    api.getProjectTasks(activeProject.id)
      .then((data) => {
        if (data.pending_tasks && data.pending_tasks.length > 0) {
          setSuggestedTask(data.pending_tasks[0])
        } else if (activeHypotheses && activeHypotheses.length > 0) {
          setSuggestedTask(`Investigate hypothesis: ${activeHypotheses[0]}`)
        } else {
          setSuggestedTask(`Perform deep passive reconnaissance on ${activeProject.target_seed}`)
        }
      })
      .catch(() => {
        setSuggestedTask(`Enrich network topology for ${activeProject.target_seed}`)
      })
  }, [activeProject?.id, activeHypotheses])

  const handleExecuteNext = async () => {
    if (!activeProject || !suggestedTask || isExecuting) return
    setIsExecuting(true)
    try {
      await api.injectTask(activeProject.id, 'wayback_lookup', { domain: activeProject.target_seed }, suggestedTask)
      setExecuted(true)
      setTimeout(() => setExecuted(false), 3000)
    } catch (err) {
      console.error('Failed to execute next action:', err)
    } finally {
      setIsExecuting(false)
    }
  }

  if (!suggestedTask) return null

  return (
    <div className="p-3.5 rounded-lg border border-accent/20 bg-bg-surface relative overflow-hidden shadow-sm">
      <div className="flex items-center justify-between gap-2 mb-1.5">
        <span className="flex items-center gap-1.5 text-2xs font-semibold text-accent uppercase tracking-wider">
          <Sparkles className="w-3.5 h-3.5" strokeWidth={1.5} />
          Suggested Next Action
        </span>
        {executed && (
          <span className="flex items-center gap-1 text-2xs text-status-confirmed">
            <CheckCircle2 className="w-3 h-3" /> Injected
          </span>
        )}
      </div>

      <p className="text-2xs text-text-secondary leading-relaxed mb-3 font-sans">
        {suggestedTask}
      </p>

      <button
        onClick={handleExecuteNext}
        disabled={isExecuting || executed}
        className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded text-2xs font-medium text-white bg-accent hover:bg-accent-hover active:bg-accent-active disabled:opacity-50 transition-colors duration-120 ease-enter"
      >
        <Play className="w-3 h-3" strokeWidth={1.5} />
        {isExecuting ? 'Injecting Plan...' : executed ? 'Task Scheduled' : 'Accept & Execute Step'}
        {!isExecuting && !executed && <ArrowRight className="w-3 h-3 ml-0.5" strokeWidth={1.5} />}
      </button>
    </div>
  )
}
