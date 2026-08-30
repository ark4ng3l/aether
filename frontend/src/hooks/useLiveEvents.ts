import { useEffect, useRef } from 'react'
import { useAuthStore } from '../stores/useAuthStore'
import { useProjectStore } from '../stores/useProjectStore'
import { useGraphStore } from '../stores/useGraphStore'
import { useTaskStore } from '../stores/useTaskStore'
import { useConsoleStore } from '../stores/useConsoleStore'
import { useNotificationStore } from '../features/notifications/useNotificationStore'
import { AnyWebSocketEvent } from '../types/events'
import { EntityType, RelationshipType } from '../types/api'

export function useLiveEvents() {
  const token = useAuthStore((s) => s.token)
  const activeProjectId = useProjectStore((s) => s.activeProjectId)
  const updateProjectStatus = useProjectStore((s) => s.updateProjectStatus)
  const incrementEntityCount = useProjectStore((s) => s.incrementEntityCount)
  const addEntityNode = useGraphStore((s) => s.addEntityNode)
  const addRelationshipEdge = useGraphStore((s) => s.addRelationshipEdge)
  const setActiveTask = useTaskStore((s) => s.setActiveTask)
  const addCompletedTask = useTaskStore((s) => s.addCompletedTask)
  const bufferToken = useConsoleStore((s) => s.bufferToken)
  const addLog = useConsoleStore((s) => s.addLog)

  const socketRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<number | null>(null)

  useEffect(() => {
    if (!token) return

    let isUnmounted = false
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host || '127.0.0.1:8000'
    const endpoint = activeProjectId ? `/ws/${activeProjectId}` : '/ws/global'
    const wsUrl = `${protocol}//${host}${endpoint}?token=${encodeURIComponent(token)}`

    function connect() {
      if (isUnmounted) return
      try {
        const ws = new WebSocket(wsUrl)
        socketRef.current = ws

        ws.onopen = () => {
          addLog({
            timestamp: new Date().toLocaleTimeString(),
            text: `[SYS] WebSocket connected to ${endpoint}`,
            type: 'info',
          })
        }

        ws.onmessage = (event) => {
          try {
            const data: AnyWebSocketEvent = JSON.parse(event.data)
            const time = data.timestamp ? new Date(data.timestamp).toLocaleTimeString() : new Date().toLocaleTimeString()

            switch (data.event) {
              case 'status_change':
                if (activeProjectId) {
                  updateProjectStatus(activeProjectId, data.status)
                }
                addLog({
                  timestamp: time,
                  text: `[STATUS] Investigation phase changed: ${data.status.toUpperCase()}`,
                  type: 'info',
                })
                break

              case 'entity_discovered':
                if (activeProjectId) {
                  incrementEntityCount(activeProjectId)
                }
                addEntityNode({
                  id: data.id,
                  type: data.type,
                  properties: data.properties || {},
                  confidence: data.confidence || 1.0,
                  confidence_signals: data.confidence_signals || [],
                  corroboration_count: 1,
                  first_seen: data.timestamp || new Date().toISOString(),
                  last_updated: data.timestamp || new Date().toISOString(),
                })
                addLog({
                  timestamp: time,
                  text: `[ENTITY] Discovered ${data.type.toUpperCase()}: ${data.id}`,
                  type: 'info',
                })
                break

              case 'entity_updated':
                addEntityNode({
                  id: data.id,
                  type: 'unknown' as EntityType,
                  properties: {},
                  confidence: data.confidence,
                  confidence_signals: data.confidence_signals || [],
                  corroboration_count: data.corroboration_count || 1,
                  first_seen: data.timestamp || new Date().toISOString(),
                  last_updated: data.timestamp || new Date().toISOString(),
                })
                break

              case 'relationship_added':
                addRelationshipEdge(data.source_id, data.target_id, data.rel_type)
                break

              case 'task_started':
                setActiveTask({
                  id: data.task_id,
                  tool_name: data.tool || data.tool_name || 'task',
                  params: data.params || {},
                  reasoning: data.reasoning || '',
                  status: 'running',
                  confidence: 0.5,
                  output_summary: '',
                  duration_seconds: 0,
                  timestamp: data.timestamp || new Date().toISOString(),
                  produced_entity_ids: [],
                })
                addLog({
                  timestamp: time,
                  text: `[TASK START] ${data.tool || data.tool_name} — Reasoning: ${data.reasoning || 'Executing plan'}`,
                  type: 'info',
                })
                break

              case 'task_completed':
                addCompletedTask({
                  id: data.task_id,
                  tool_name: data.tool || data.tool_name || 'task',
                  params: {},
                  reasoning: '',
                  critic_reasoning: data.critic_reasoning,
                  status: data.status,
                  verdict: data.verdict,
                  confidence: data.confidence,
                  confidence_breakdown: data.confidence_breakdown,
                  output_summary: data.summary || '',
                  duration_seconds: data.duration || 0,
                  timestamp: data.timestamp || new Date().toISOString(),
                  produced_entity_ids: data.produced_entity_ids || [],
                })
                setActiveTask(null)

                const verdictLabel = data.verdict ? ` [${data.verdict}]` : ''
                const criticText = data.critic_reasoning ? `\n  Critic: ${data.critic_reasoning}` : ''
                addLog({
                  timestamp: time,
                  text: `[TASK COMPLETED] ${data.tool || data.tool_name}${verdictLabel} (Conf: ${data.confidence.toFixed(2)})${criticText}`,
                  type: data.verdict === 'CONFIRMED' ? 'verdict' : 'info',
                })
                break

              case 'task_failed':
                setActiveTask(null)
                addLog({
                  timestamp: time,
                  text: `[TASK FAILED] ${data.tool}: ${data.error}`,
                  type: 'error',
                })
                break

              case 'token_stream':
                if (data.token) {
                  bufferToken(data.token, 'token')
                }
                break

              case 'tool_skipped_degraded':
                addLog({
                  timestamp: time,
                  text: `[CIRCUIT BREAKER] Tool '${data.tool_name}' skipped: ${data.reason}`,
                  type: 'warn',
                })
                useNotificationStore.getState().addNotification({
                  type: 'tool_degraded',
                  title: `Tool Degraded: ${data.tool_name}`,
                  description: data.reason,
                  timestamp: new Date().toISOString(),
                  navigateTo: 'arsenal',
                })
                break

              case 'dossier_ready':
                addLog({
                  timestamp: time,
                  text: `[DOSSIER] Intelligence dossier successfully synthesized and verified`,
                  type: 'verdict',
                })
                useNotificationStore.getState().addNotification({
                  type: 'dossier_ready',
                  title: 'Intelligence Dossier Ready',
                  description: 'Comprehensive report has been synthesized and verified.',
                  timestamp: new Date().toISOString(),
                  navigateTo: 'dossier',
                })
                break

              case 'investigation_completed':
                if (activeProjectId) {
                  updateProjectStatus(activeProjectId, 'completed')
                }
                addLog({
                  timestamp: time,
                  text: `[COMPLETE] Investigation finished. Discovered ${data.entities_count} entities in ${data.duration_seconds}s.`,
                  type: 'verdict',
                })
                useNotificationStore.getState().addNotification({
                  type: 'investigation_completed',
                  title: 'Investigation Completed',
                  description: `Found ${data.entities_count} entities in ${data.duration_seconds}s.`,
                  timestamp: new Date().toISOString(),
                  navigateTo: 'overview',
                })
                break
            }
          } catch (err) {
            console.error('Error handling WebSocket message:', err)
          }
        }

        ws.onclose = () => {
          if (!isUnmounted) {
            reconnectTimeoutRef.current = window.setTimeout(connect, 3000)
          }
        }

        ws.onerror = (err) => {
          console.warn('WebSocket connection error:', err)
          ws.close()
        }
      } catch (err) {
        if (!isUnmounted) {
          reconnectTimeoutRef.current = window.setTimeout(connect, 3000)
        }
      }
    }

    connect()

    return () => {
      isUnmounted = true
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (socketRef.current) {
        socketRef.current.close()
      }
    }
  }, [token, activeProjectId])
}
