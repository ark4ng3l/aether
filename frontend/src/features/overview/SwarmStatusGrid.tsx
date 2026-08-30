import React from 'react'
import {
  Brain,
  Globe,
  Eye,
  ShieldAlert,
  Zap,
  Activity,
  CheckCircle,
  Clock,
  RotateCcw,
} from 'lucide-react'
import { useLocaleStore } from '../../stores/useLocaleStore'
import { TaskStep } from '../../types/api'

interface SwarmStatusGridProps {
  status: string
  completedTasks: TaskStep[]
  activeTask: TaskStep | null
}

export const SwarmStatusGrid: React.FC<SwarmStatusGridProps> = ({
  status,
  completedTasks,
  activeTask,
}) => {
  const { t } = useLocaleStore()
  const isRunning = ['planning', 'collecting', 'reasoning', 'verifying', 'synthesizing'].includes(status)

  // Count actions per agent
  const networkCount = completedTasks.filter((t) =>
    ['subdomain_finder', 'ip_geolocate', 'network_recon', 'whois_lookup', 'shodan_lookup', 'tls_cert_inspector', 'wayback_archive'].includes(t.tool_name)
  ).length

  const visionCount = completedTasks.filter((t) =>
    ['image_osint', 'vlm_processor', 'metadata_extractor'].includes(t.tool_name)
  ).length

  const criticCount = completedTasks.filter((t) => Boolean(t.verdict)).length
  const confirmedCount = completedTasks.filter((t) => t.verdict === 'CONFIRMED').length

  const agents = [
    {
      id: 'commander',
      name: t('overview.commanderAgent', 'Commander Agent'),
      role: 'Goal Decomposition & Strategy',
      icon: Brain,
      color: 'purple',
      badge: status === 'planning' ? 'Planning...' : status === 'reasoning' ? 'Hypothesis' : 'Online',
      active: status === 'planning' || status === 'reasoning',
      metric: `${completedTasks.length} Plans Executed`,
      detail: activeTask ? `Dispatching: ${activeTask.tool_name}` : 'Awaiting new evidence or user directives',
    },
    {
      id: 'network',
      name: t('overview.networkSpecialist', 'Network Specialist'),
      role: 'DNS, BGP, Shodan & WHOIS',
      icon: Globe,
      color: 'blue',
      badge: activeTask && ['subdomain_finder', 'ip_geolocate', 'network_recon', 'whois_lookup'].includes(activeTask.tool_name) ? 'Probing...' : 'Standby',
      active: activeTask && ['subdomain_finder', 'ip_geolocate', 'network_recon', 'whois_lookup'].includes(activeTask.tool_name),
      metric: `${networkCount} Probes Ran`,
      detail: 'Monitoring passive intelligence repositories',
    },
    {
      id: 'vision',
      name: t('overview.visionSpecialist', 'Vision Specialist'),
      role: 'VLM OCR & Satellite Geolocation',
      icon: Eye,
      color: 'cyan',
      badge: activeTask && ['image_osint', 'vlm_processor'].includes(activeTask.tool_name) ? 'Analyzing...' : 'Standby',
      active: activeTask && ['image_osint', 'vlm_processor'].includes(activeTask.tool_name),
      metric: `${visionCount} Frames Analyzed`,
      detail: 'Qwen3VL-8B local neural perception engine',
    },
    {
      id: 'critic',
      name: t('overview.criticAgent', 'Red Team Critic & Healing'),
      role: 'Adversarial Verification & Resilience',
      icon: ShieldAlert,
      color: 'emerald',
      badge: status === 'verifying' ? 'Verifying...' : 'Monitoring',
      active: status === 'verifying',
      metric: `${confirmedCount}/${criticCount || 1} Verified`,
      detail: 'Multi-signal corroboration & fault auto-healing',
    },
  ]

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 my-4">
      {agents.map((agent) => {
        const Icon = agent.icon
        return (
          <div
            key={agent.id}
            className={`relative overflow-hidden bg-bg-surface border rounded-xl p-3.5 transition-all duration-200 shadow-sm ${
              agent.active
                ? 'border-accent/40 bg-accent-subtle/10 shadow-md ring-1 ring-accent/20'
                : 'border-border-subtle hover:border-border-strong'
            }`}
          >
            <div className="flex items-start justify-between gap-2 mb-2">
              <div className="flex items-center gap-2.5">
                <div
                  className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
                    agent.color === 'purple'
                      ? 'bg-purple-500/10 text-purple-400'
                      : agent.color === 'blue'
                      ? 'bg-blue-500/10 text-blue-400'
                      : agent.color === 'cyan'
                      ? 'bg-cyan-500/10 text-cyan-400'
                      : 'bg-emerald-500/10 text-emerald-400'
                  }`}
                >
                  <Icon className="w-4 h-4" strokeWidth={1.75} />
                </div>
                <div>
                  <h4 className="text-2xs font-semibold text-text-primary leading-tight">{agent.name}</h4>
                  <p className="text-[10px] text-text-tertiary truncate">{agent.role}</p>
                </div>
              </div>

              <span
                className={`text-[9px] font-mono font-medium px-2 py-0.5 rounded-full border ${
                  agent.active
                    ? 'bg-accent/10 text-accent border-accent/30 animate-pulse'
                    : 'bg-bg-canvas text-text-tertiary border-border-subtle'
                }`}
              >
                {agent.badge}
              </span>
            </div>

            <div className="pt-2 border-t border-border-subtle/50 flex items-center justify-between text-2xs">
              <span className="font-mono font-medium text-text-primary">{agent.metric}</span>
              <span className="text-[10px] text-text-tertiary truncate max-w-[120px]">{agent.detail}</span>
            </div>
          </div>
        )
      })}
    </div>
  )
}
