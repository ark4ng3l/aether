import React, { useState } from 'react'
import {
  Brain,
  Sparkles,
  ShieldCheck,
  Zap,
  Activity,
  Send,
  CheckCircle2,
  AlertTriangle,
  Flame,
  Search,
  Eye,
  CornerDownLeft,
} from 'lucide-react'
import { TaskStep } from '../../types/api'
import { LogEntry } from '../../stores/useConsoleStore'
import { useLocaleStore } from '../../stores/useLocaleStore'
import { showToast } from '../../components/ui/Toast'
import { api } from '../../api/endpoints'

interface CognitiveReasoningHUDProps {
  projectId: string
  status: string
  activeTask: TaskStep | null
  completedTasks: TaskStep[]
  logs: LogEntry[]
  onTaskInjected?: () => void
}

export const CognitiveReasoningHUD: React.FC<CognitiveReasoningHUDProps> = ({
  projectId,
  status,
  activeTask,
  completedTasks,
  logs,
  onTaskInjected,
}) => {
  const { t } = useLocaleStore()
  const [injectionPrompt, setInjectionPrompt] = useState('')
  const [isInjecting, setIsInjecting] = useState(false)
  const [activeFilter, setActiveFilter] = useState<'all' | 'reasoning' | 'verdicts' | 'errors'>('all')

  const handleInjectTask = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!injectionPrompt.trim() || isInjecting) return

    setIsInjecting(true)
    try {
      await api.injectTask(
        projectId,
        'web_search',
        { query: injectionPrompt.trim() },
        `User Prompt Injection: ${injectionPrompt.trim()}`
      )
      showToast({ message: 'Instruction injected into Commander reasoning stack!', type: 'success' })
      setInjectionPrompt('')
      onTaskInjected?.()
    } catch (err: any) {
      showToast({ message: err?.message || 'Failed to inject instruction', type: 'error' })
    } finally {
      setIsInjecting(false)
    }
  }


  // Filter relevant logs for the cognitive stream
  const cognitiveLogs = logs
    .filter((l) => {
      if (activeFilter === 'reasoning') return l.text.includes('[CoT]') || l.text.includes('[Planner]') || l.text.includes('[Commander]') || l.type === 'info'
      if (activeFilter === 'verdicts') return l.type === 'verdict' || l.text.includes('Verdict') || l.text.includes('CONFIRMED')
      if (activeFilter === 'errors') return l.type === 'error' || l.type === 'warn'
      return true
    })
    .slice(-30)
    .reverse()

  const latestCompleted = completedTasks[completedTasks.length - 1]

  return (
    <div className="bg-bg-surface border border-border-subtle rounded-xl p-4 shadow-sm flex flex-col h-full">
      {/* HUD Header */}
      <div className="flex items-center justify-between pb-3 border-b border-border-subtle">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-purple-500/10 border border-purple-500/20 flex items-center justify-center">
            <Brain className="w-4 h-4 text-purple-400 animate-pulse" />
          </div>
          <div>
            <h3 className="text-xs font-semibold text-text-primary">
              {t('overview.cognitiveStream', 'Cognitive Reasoning & Inner Monologue')}
            </h3>
            <p className="text-[10px] text-text-tertiary">
              {t('overview.modelThoughts', 'Live Tree-of-Thought & Chain-of-Thought trace')}
            </p>
          </div>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-1 bg-bg-canvas p-0.5 rounded-lg border border-border-subtle text-[10px]">
          <button
            onClick={() => setActiveFilter('all')}
            className={`px-2 py-0.5 rounded-md transition-colors ${
              activeFilter === 'all' ? 'bg-bg-surface text-accent font-medium shadow-xs' : 'text-text-tertiary hover:text-text-primary'
            }`}
          >
            All
          </button>
          <button
            onClick={() => setActiveFilter('reasoning')}
            className={`px-2 py-0.5 rounded-md transition-colors ${
              activeFilter === 'reasoning' ? 'bg-bg-surface text-purple-400 font-medium shadow-xs' : 'text-text-tertiary hover:text-text-primary'
            }`}
          >
            CoT Reasoning
          </button>
          <button
            onClick={() => setActiveFilter('verdicts')}
            className={`px-2 py-0.5 rounded-md transition-colors ${
              activeFilter === 'verdicts' ? 'bg-bg-surface text-emerald-400 font-medium shadow-xs' : 'text-text-tertiary hover:text-text-primary'
            }`}
          >
            Verdicts
          </button>
          <button
            onClick={() => setActiveFilter('errors')}
            className={`px-2 py-0.5 rounded-md transition-colors ${
              activeFilter === 'errors' ? 'bg-bg-surface text-rose-400 font-medium shadow-xs' : 'text-text-tertiary hover:text-text-primary'
            }`}
          >
            Healed
          </button>
        </div>
      </div>

      {/* Active Model Reasoning Spotlight */}
      {activeTask && (
        <div className="my-3 p-3 bg-gradient-to-r from-purple-500/10 via-accent/5 to-transparent border border-purple-500/30 rounded-xl relative overflow-hidden animate-fade-in">
          <div className="flex items-center justify-between gap-2 mb-1.5">
            <div className="flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-purple-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-purple-500" />
              </span>
              <span className="text-2xs font-mono font-semibold text-purple-400 uppercase tracking-wider">
                ⚡ Active Reasoning Step: {activeTask.tool_name}
              </span>
            </div>
            <span className="text-[10px] font-mono text-text-tertiary">PID #{activeTask.id.slice(0, 8)}</span>
          </div>

          {activeTask.reasoning && (
            <p className="text-2xs text-text-primary font-sans leading-relaxed pl-4 border-l-2 border-purple-500/50 rtl:pl-0 rtl:pr-4 rtl:border-l-0 rtl:border-r-2 my-1">
              "{activeTask.reasoning}"
            </p>
          )}

          {activeTask.params && Object.keys(activeTask.params).length > 0 && (
            <div className="mt-2 text-[10px] font-mono bg-bg-canvas/80 p-1.5 rounded border border-border-subtle/60 text-text-secondary truncate">
              Params: {JSON.stringify(activeTask.params)}
            </div>
          )}
        </div>
      )}

      {/* Latest Adversarial Critic Verdict Card */}
      {latestCompleted?.critic_reasoning && (
        <div className="mb-3 p-2.5 bg-bg-canvas border border-border-strong/40 rounded-lg flex items-start gap-2.5">
          <div className="mt-0.5 shrink-0">
            {latestCompleted.verdict === 'CONFIRMED' ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            ) : latestCompleted.verdict === 'REJECTED' ? (
              <AlertTriangle className="w-4 h-4 text-rose-400" />
            ) : (
              <ShieldCheck className="w-4 h-4 text-amber-400" />
            )}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between gap-2">
              <span className="text-2xs font-semibold text-text-primary flex items-center gap-1.5">
                <span>{t('overview.criticAgent', 'Red Team Critic')}</span>
                <span
                  className={`text-[9px] font-mono px-1.5 py-0.2 rounded font-bold ${
                    latestCompleted.verdict === 'CONFIRMED'
                      ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                      : latestCompleted.verdict === 'REJECTED'
                      ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                      : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                  }`}
                >
                  {latestCompleted.verdict || 'PLAUSIBLE'} ({Math.round((latestCompleted.confidence || 0.8) * 100)}%)
                </span>
              </span>
              <span className="text-[10px] text-text-tertiary">{latestCompleted.tool_name}</span>
            </div>
            <p className="text-[11px] text-text-secondary mt-0.5 line-clamp-2">
              {latestCompleted.critic_reasoning}
            </p>
          </div>
        </div>
      )}

      {/* Live Stream Logs / Thought Terminal */}
      <div className="flex-1 overflow-y-auto max-h-[360px] space-y-1 pr-1 scrollbar-thin">
        {cognitiveLogs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center text-text-tertiary">
            <Brain className="w-8 h-8 opacity-20 mb-2" />
            <p className="text-2xs">{t('overview.noActivity', 'No activity yet. Start an investigation to see live events.')}</p>
          </div>
        ) : (
          cognitiveLogs.map((log) => {
            const isVerdict = log.type === 'verdict' || log.text.includes('[VERDICT]')
            const isError = log.type === 'error' || log.type === 'warn'
            const isReasoning = log.text.includes('[CoT]') || log.text.includes('[Planner]') || log.text.includes('[Commander]')

            return (
              <div
                key={log.id}
                className={`p-2 rounded-lg text-2xs transition-colors flex items-start gap-2 border ${
                  isVerdict
                    ? 'bg-emerald-500/5 border-emerald-500/20 text-emerald-300'
                    : isError
                    ? 'bg-rose-500/5 border-rose-500/20 text-rose-300'
                    : isReasoning
                    ? 'bg-purple-500/5 border-purple-500/20 text-purple-300'
                    : 'bg-bg-canvas/50 border-border-subtle/40 text-text-secondary hover:bg-bg-canvas'
                }`}
              >
                <span className="font-mono text-[10px] text-text-tertiary shrink-0 mt-0.5 w-14">
                  {log.timestamp}
                </span>
                <div className="flex-1 min-w-0">
                  <span className="break-words leading-relaxed">{log.text}</span>
                </div>
              </div>
            )
          })
        )}
      </div>

      {/* Direct Thought & Instruction Injection Bar */}
      <form onSubmit={handleInjectTask} className="mt-3 pt-3 border-t border-border-subtle relative">
        <div className="relative flex items-center">
          <input
            type="text"
            value={injectionPrompt}
            onChange={(e) => setInjectionPrompt(e.target.value)}
            placeholder={t('overview.injectPlaceholder', 'Instruct the Commander agent (e.g. Focus on exposed subdomains)...')}
            className="w-full pl-3 pr-24 rtl:pl-24 rtl:pr-3 py-2 text-2xs bg-bg-canvas border border-border-strong/60 rounded-lg text-text-primary placeholder:text-text-tertiary focus:border-accent focus:ring-1 focus:ring-accent outline-none transition-all shadow-inner"
          />
          <button
            type="submit"
            disabled={!injectionPrompt.trim() || isInjecting}
            className="absolute right-1.5 rtl:right-auto rtl:left-1.5 flex items-center gap-1 px-2.5 py-1 text-[11px] font-medium text-white bg-accent hover:bg-accent-hover disabled:opacity-40 disabled:cursor-not-allowed rounded-md transition-colors"
          >
            <span>{t('overview.injectButton', 'Inject')}</span>
            <CornerDownLeft className="w-3 h-3" />
          </button>
        </div>
      </form>
    </div>
  )
}
