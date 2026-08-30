import React, { useState, useMemo } from 'react'
import {
  Clock,
  CheckCircle2,
  AlertTriangle,
  Radio,
  ExternalLink,
  ChevronDown,
  ChevronRight,
  Shield,
  Layers,
} from 'lucide-react'
import { useTaskStore } from '../../stores/useTaskStore'
import { useProjectStore } from '../../stores/useProjectStore'
import { useGraphStore } from '../../stores/useGraphStore'
import { TaskStep } from '../../types/api'
import { ConfidenceBadge } from '../../components/ui/ConfidenceBadge'
import { EmptyState } from '../../components/ui/EmptyState'
import { TimelineFilterBar } from './TimelineFilterBar'

export const TimelineTab: React.FC = () => {
  const { completedTasks, activeTask } = useTaskStore()
  const { activeProject, setActiveTab, setSelectedEntityId, setIsNewModalOpen } = useProjectStore()
  const { nodes } = useGraphStore()

  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [confidenceFilter, setConfidenceFilter] = useState(0)
  const [toolFilter, setToolFilter] = useState('all')
  const [expandedTasks, setExpandedTasks] = useState<Record<string, boolean>>({})

  const toggleExpand = (id: string) => {
    setExpandedTasks((prev) => ({ ...prev, [id]: !prev[id] }))
  }

  // Available unique tools
  const availableTools = useMemo(() => {
    const tools = new Set(completedTasks.map((t) => t.tool_name))
    return Array.from(tools).sort()
  }, [completedTasks])

  // Filter tasks
  const filteredTasks = useMemo(() => {
    return completedTasks.filter((task) => {
      if (statusFilter !== 'all' && task.status !== statusFilter) return false
      if (toolFilter !== 'all' && task.tool_name !== toolFilter) return false
      if (task.confidence < confidenceFilter) return false
      if (searchQuery) {
        const q = searchQuery.toLowerCase()
        const matchName = task.tool_name.toLowerCase().includes(q)
        const matchReason = (task.reasoning || '').toLowerCase().includes(q)
        const matchSummary = (task.output_summary || '').toLowerCase().includes(q)
        if (!matchName && !matchReason && !matchSummary) return false
      }
      return true
    })
  }, [completedTasks, statusFilter, toolFilter, confidenceFilter, searchQuery])

  // Group by date string (YYYY-MM-DD)
  const groupedTasks = useMemo(() => {
    const groups: Record<string, TaskStep[]> = {}
    filteredTasks.forEach((task) => {
      const dateKey = task.timestamp ? task.timestamp.split('T')[0] : 'Unknown Date'
      if (!groups[dateKey]) groups[dateKey] = []
      groups[dateKey].push(task)
    })
    return groups
  }, [filteredTasks])

  const handleEntityChipClick = (entityId: string) => {
    setSelectedEntityId(entityId)
    setActiveTab('graph')
  }

  if (!activeProject) {
    return (
      <EmptyState
        icon={Shield}
        title="No active investigation"
        description="Select or start an investigation to inspect its analytical timeline."
        action={{ label: 'New Investigation', onClick: () => setIsNewModalOpen(true) }}
      />
    )
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-bg-canvas">
      {/* Filter Bar */}
      <TimelineFilterBar
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        confidenceFilter={confidenceFilter}
        onConfidenceFilterChange={setConfidenceFilter}
        toolFilter={toolFilter}
        onToolFilterChange={setToolFilter}
        availableTools={availableTools}
        totalCount={filteredTasks.length}
      />

      {/* Task List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {/* Active Task (if running) */}
        {activeTask && (
          <div className="p-3.5 rounded-lg border border-accent/30 bg-accent-subtle animate-fade-in shadow-sm">
            <div className="flex items-center justify-between mb-1">
              <span className="flex items-center gap-1.5 text-2xs font-semibold text-accent">
                <Radio className="w-3.5 h-3.5 animate-pulse" />
                Active Execution: {activeTask.tool_name}
              </span>
              <span className="text-2xs text-text-tertiary font-mono-data">In Progress</span>
            </div>
            {activeTask.reasoning && (
              <p className="text-2xs text-text-secondary leading-snug">{activeTask.reasoning}</p>
            )}
          </div>
        )}

        {filteredTasks.length === 0 && !activeTask ? (
          <EmptyState
            icon={Clock}
            title="No timeline events"
            description={completedTasks.length > 0 ? "No events match the selected filters." : "Run the investigation to populate the analytical event timeline."}
          />
        ) : (
          Object.entries(groupedTasks).map(([date, tasks]) => (
            <div key={date} className="space-y-2">
              {/* Sticky Date Header */}
              <div className="sticky top-0 z-10 py-1 bg-bg-canvas/90 backdrop-blur-sm border-b border-border-subtle">
                <span className="text-2xs font-bold text-text-tertiary uppercase tracking-wider font-mono-data">
                  {date} ({tasks.length} actions)
                </span>
              </div>

              {/* Day events */}
              <div className="space-y-2 pl-2 border-l border-border-subtle">
                {tasks.map((task) => {
                  const isExpanded = !!expandedTasks[task.id]
                  const isSuccess = task.status === 'completed'

                  return (
                    <div
                      key={task.id}
                      className="p-3 rounded-lg border border-border-subtle bg-bg-surface hover:border-border-strong transition-all duration-120 shadow-sm"
                    >
                      {/* Top row */}
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex items-center gap-2 min-w-0">
                          {isSuccess ? (
                            <CheckCircle2 className="w-4 h-4 text-status-confirmed shrink-0" />
                          ) : (
                            <AlertTriangle className="w-4 h-4 text-status-rejected shrink-0" />
                          )}
                          <h4 className="text-xs font-bold text-text-primary font-mono-data truncate">
                            {task.tool_name}
                          </h4>
                          {task.verdict && (
                            <span
                              className={`text-[10px] font-semibold px-1.5 py-0.2 rounded border ${
                                task.verdict === 'CONFIRMED'
                                  ? 'text-status-confirmed border-status-confirmed/30 bg-status-confirmed/10'
                                  : task.verdict === 'PLAUSIBLE'
                                  ? 'text-status-plausible border-status-plausible/30 bg-status-plausible/10'
                                  : 'text-status-rejected border-status-rejected/30 bg-status-rejected/10'
                              }`}
                            >
                              {task.verdict}
                            </span>
                          )}
                        </div>

                        <div className="flex items-center gap-2 shrink-0">
                          <ConfidenceBadge score={task.confidence} />
                          <span className="text-2xs text-text-tertiary font-mono-data">
                            {task.timestamp ? new Date(task.timestamp).toLocaleTimeString() : ''}
                          </span>
                        </div>
                      </div>

                      {/* Reasoning Summary */}
                      {task.reasoning && (
                        <p className="text-2xs text-text-secondary mt-1.5 leading-relaxed font-sans">
                          {task.reasoning}
                        </p>
                      )}

                      {/* Critic Reasoning */}
                      {task.critic_reasoning && (
                        <div className="mt-2 p-2 rounded bg-status-confirmed/5 border border-status-confirmed/20 text-2xs text-status-confirmed">
                          <span className="font-semibold">Critic Refutation:</span> {task.critic_reasoning}
                        </div>
                      )}

                      {/* Provenance Entity Chip Row */}
                      {task.produced_entity_ids && task.produced_entity_ids.length > 0 && (
                        <div className="flex flex-wrap items-center gap-1.5 mt-2.5 pt-2 border-t border-border-subtle">
                          <span className="text-[11px] text-text-tertiary flex items-center gap-1 shrink-0">
                            <Layers className="w-3 h-3" /> Produced:
                          </span>
                          {task.produced_entity_ids.map((eid) => (
                            <button
                              key={eid}
                              onClick={() => handleEntityChipClick(eid)}
                              className="px-2 py-0.5 rounded text-[11px] font-mono-data bg-bg-canvas border border-border-subtle hover:border-accent hover:text-accent transition-colors truncate max-w-[200px]"
                            >
                              {eid}
                            </button>
                          ))}
                        </div>
                      )}

                      {/* Output Summary toggle */}
                      {task.output_summary && (
                        <div className="mt-2">
                          <button
                            onClick={() => toggleExpand(task.id)}
                            className="flex items-center gap-1 text-[11px] text-text-tertiary hover:text-text-primary transition-colors"
                          >
                            {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                            {isExpanded ? 'Hide Raw Output' : 'View Raw Output'}
                          </button>
                          {isExpanded && (
                            <pre className="mt-1.5 p-2 rounded bg-bg-canvas border border-border-subtle text-[11px] font-mono-data text-text-secondary overflow-x-auto whitespace-pre-wrap max-h-48">
                              {task.output_summary}
                            </pre>
                          )}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
