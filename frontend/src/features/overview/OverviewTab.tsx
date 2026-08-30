import React, { useState } from 'react'
import { Shield } from 'lucide-react'
import { useProjectStore } from '../../stores/useProjectStore'
import { useTaskStore } from '../../stores/useTaskStore'
import { useGraphStore } from '../../stores/useGraphStore'
import { useConsoleStore } from '../../stores/useConsoleStore'
import { useLocaleStore } from '../../stores/useLocaleStore'
import { api } from '../../api/endpoints'
import { EmptyState } from '../../components/ui/EmptyState'
import { ProgressRail } from './ProgressRail'
import { TacticalMissionHUD } from './TacticalMissionHUD'
import { SwarmStatusGrid } from './SwarmStatusGrid'
import { CognitiveReasoningHUD } from './CognitiveReasoningHUD'
import { IntelligenceBentoFeed } from './IntelligenceBentoFeed'
import { MissionTelemetryBar } from './MissionTelemetryBar'

export const OverviewTab: React.FC = () => {
  const { activeProject, updateProjectStatus, setIsNewModalOpen } = useProjectStore()
  const { completedTasks, activeTask } = useTaskStore()
  const { nodes } = useGraphStore()
  const { logs } = useConsoleStore()
  const { t } = useLocaleStore()
  const [isInjectModalOpen, setIsInjectModalOpen] = useState(false)

  if (!activeProject) {
    return (
      <EmptyState
        icon={Shield}
        title={t('project.noProjects', 'No active investigation selected')}
        description={t(
          'overview.emptyDescription',
          'Select a target from the left rail or initialize a new target seed to begin autonomous OSINT reconnaissance.'
        )}
        action={{
          label: t('nav.newInvestigation', 'New Investigation'),
          onClick: () => setIsNewModalOpen(true),
        }}
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

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-4 animate-slide-up">
      {/* 1. Tactical Mission HUD Header */}
      <TacticalMissionHUD
        project={activeProject}
        isRunning={isRunning}
        onRun={handleRun}
        onStop={handleStop}
        onOpenInjectModal={() => {
          const el = document.querySelector('input[placeholder*="Commander"]') as HTMLInputElement
          if (el) el.focus()
        }}
      />

      {/* 2. Investigation Lifecycle Progress Rail */}
      <ProgressRail status={status} />

      {/* 3. Autonomous Multi-Agent Swarm Status Cards */}
      <SwarmStatusGrid
        status={status}
        completedTasks={completedTasks}
        activeTask={activeTask}
      />

      {/* 4. Main 2-Column Tactical Intelligence Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-stretch">
        {/* Left Column: Cognitive CoT & Model Inner Monologue */}
        <div className="min-h-[460px]">
          <CognitiveReasoningHUD
            projectId={activeProject.id}
            status={status}
            activeTask={activeTask}
            completedTasks={completedTasks}
            logs={logs}
          />
        </div>

        {/* Right Column: Discovered Intelligence Bento Feed */}
        <div className="min-h-[460px]">
          <IntelligenceBentoFeed nodes={nodes} />
        </div>
      </div>

      {/* 5. Telemetry & Resilience Health Bar */}
      <MissionTelemetryBar entityCount={entityCount} taskCount={taskCount} />
    </div>
  )
}
