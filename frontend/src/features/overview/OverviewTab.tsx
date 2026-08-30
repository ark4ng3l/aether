import React from 'react'
import {
  Play,
  Square,
  ArrowRight,
  Layers,
  CheckCircle,
  Activity,
  Sparkles,
  Shield,
} from 'lucide-react'
import { useProjectStore } from '../../stores/useProjectStore'
import { useTaskStore } from '../../stores/useTaskStore'
import { useGraphStore } from '../../stores/useGraphStore'
import { useConsoleStore } from '../../stores/useConsoleStore'
import { useLocaleStore } from '../../stores/useLocaleStore'
import { api } from '../../api/endpoints'
import { EmptyState } from '../../components/ui/EmptyState'
import { StatusDot } from '../../components/ui/StatusDot'
import { ProgressRail } from './ProgressRail'
import { SparklineCard } from './SparklineCard'
import { NextActionCard } from './NextActionCard'

export const OverviewTab: React.FC = () => {
  const { activeProject, setActiveTab, updateProjectStatus, setIsNewModalOpen } = useProjectStore()
  const { completedTasks, activeTask } = useTaskStore()
  const { nodes } = useGraphStore()
  const { logs } = useConsoleStore()
  const { t } = useLocaleStore()

  if (!activeProject) {
    return (
      <EmptyState
        icon={Shield}
        title={t('project.noProjects', 'No active investigation selected')}
        description={t('overview.emptyDescription', 'Select a target from the left rail or initialize a new target seed to begin autonomous OSINT reconnaissance.')}
        action={{ label: t('nav.newInvestigation', 'New Investigation'), onClick: () => setIsNewModalOpen(true) }}
      />
    )
  }

  const status = activeProject.status
  const isRunning = ['planning', 'collecting', 'reasoning', 'verifying', 'synthesizing'].includes(status)
  const entityCount = nodes.length || activeProject.entities_count
  const taskCount = completedTasks.length || activeProject.completed_tasks_count

  const handleRun = async () => {
    try {
      await api.runProject(activeProject.id)
      updateProjectStatus(activeProject.id, 'planning')
    } catch (err) {
      console.error(err)
    }
  }

  const handleStop = async () => {
    try {
      await api.stopProject(activeProject.id)
      updateProjectStatus(activeProject.id, 'stopped')
    } catch (err) {
      console.error(err)
    }
  }

  // Recent activity from logs
  const recentLogs = logs
    .filter((l) => l.type !== 'token')
    .slice(-20)
    .reverse()

  return (
    <div className="flex-1 overflow-y-auto p-4 animate-slide-up">
      {/* Target header & controls */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3 min-w-0">
          <div>
            <h2 className="text-lg font-semibold text-text-primary">{activeProject.name}</h2>
            <p className="text-2xs text-text-tertiary font-mono-data">{activeProject.target_seed}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {!isRunning && status !== 'completed' && (
            <button
              onClick={handleRun}
              className="flex items-center gap-1.5 px-3 py-1.5 text-2xs font-medium text-white bg-accent rounded hover:bg-accent-hover transition-colors duration-120"
            >
              <Play className="w-3.5 h-3.5" strokeWidth={1.5} />
              {t('overview.runMission', 'Run Mission')}
            </button>
          )}
          {isRunning && (
            <button
              onClick={handleStop}
              className="flex items-center gap-1.5 px-3 py-1.5 text-2xs font-medium text-status-rejected border border-status-rejected/30 rounded hover:bg-status-rejected/10 transition-colors duration-120"
            >
              <Square className="w-3.5 h-3.5" strokeWidth={1.5} />
              {t('overview.stopMission', 'Stop')}
            </button>
          )}
        </div>
      </div>

      {/* Progress Rail */}
      <ProgressRail status={status} />

      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4 mt-4">
        {/* Left: Activity Timeline (60%) */}
        <div className="lg:col-span-3 space-y-1">
          <h3 className="text-xs font-medium text-text-secondary mb-2 flex items-center gap-1.5">
            <Activity className="w-3.5 h-3.5" strokeWidth={1.5} />
            {t('overview.liveActivity', 'Live Activity')}
          </h3>

          {/* Active task */}
          {activeTask && (
            <div className="px-3 py-2.5 bg-accent-subtle border border-accent/20 rounded-lg mb-2 animate-fade-in">
              <div className="flex items-center gap-2">
                <StatusDot status="running" />
                <span className="text-2xs font-medium text-accent">{activeTask.tool_name}</span>
              </div>
              {activeTask.reasoning && (
                <p className="text-2xs text-text-secondary mt-1 ml-5 rtl:ml-0 rtl:mr-5">{activeTask.reasoning}</p>
              )}
            </div>
          )}

          {/* Log entries */}
          <div className="space-y-0.5 max-h-[400px] overflow-y-auto scrollbar-none">
            {recentLogs.length === 0 ? (
              <p className="text-2xs text-text-tertiary py-4 text-center">
                {t('overview.noActivity', 'No activity yet. Start an investigation to see live events.')}
              </p>
            ) : (
              recentLogs.map((log) => (
                <div
                  key={log.id}
                  className="flex items-start gap-2 px-2.5 py-1.5 rounded hover:bg-bg-canvas transition-colors duration-120"
                >
                  <span className="text-2xs text-text-tertiary font-mono-data shrink-0 mt-0.5 w-16">
                    {log.timestamp}
                  </span>
                  <span
                    className={`text-2xs flex-1 ${
                      log.type === 'error'
                        ? 'text-status-rejected'
                        : log.type === 'warn'
                        ? 'text-status-plausible'
                        : log.type === 'verdict'
                        ? 'text-status-confirmed'
                        : 'text-text-secondary'
                    }`}
                  >
                    {log.text}
                  </span>
                </div>
              ))
            )}
          </div>

          {recentLogs.length > 0 && (
            <button
              onClick={() => setActiveTab('console')}
              className="flex items-center gap-1 text-2xs text-accent hover:text-accent-hover transition-colors duration-120 mt-2"
            >
              {t('overview.viewFullConsole', 'View full console')} <ArrowRight className="w-3 h-3 rtl:rotate-180" strokeWidth={1.5} />
            </button>
          )}
        </div>

        {/* Right: Stats & Next Action (40%) */}
        <div className="lg:col-span-2 space-y-3">
          {/* Sparkline metric cards */}
          <SparklineCard
            label={t('overview.entitiesDiscovered', 'Entities Discovered')}
            value={entityCount}
            icon={Layers}
            color="#4f9dff"
          />
          <SparklineCard
            label={t('overview.tasksCompleted', 'Tasks Completed')}
            value={taskCount}
            icon={CheckCircle}
            color="#16a34a"
          />

          {/* Next Best Action */}
          <NextActionCard />

          {/* Quick nav cards */}
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => setActiveTab('graph')}
              className="flex flex-col items-center gap-1 p-3 rounded-lg border border-border-subtle hover:border-accent/30 hover:bg-accent-subtle transition-all duration-120 text-center"
            >
              <Layers className="w-4 h-4 text-text-tertiary" strokeWidth={1.5} />
              <span className="text-2xs font-medium text-text-secondary">{t('tabs.graph', 'Graph')}</span>
            </button>
            <button
              onClick={() => setActiveTab('dossier')}
              className="flex flex-col items-center gap-1 p-3 rounded-lg border border-border-subtle hover:border-accent/30 hover:bg-accent-subtle transition-all duration-120 text-center"
            >
              <Sparkles className="w-4 h-4 text-text-tertiary" strokeWidth={1.5} />
              <span className="text-2xs font-medium text-text-secondary">{t('tabs.dossier', 'Dossier')}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

