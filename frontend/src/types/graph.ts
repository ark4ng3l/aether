import { EntityType } from './api'

export interface CytoscapeNodeData {
  id: string
  label: string
  type: EntityType
  confidence: number
  corroboration_count?: number
  properties?: Record<string, any>
  confidence_signals?: any[]
  is_seed?: boolean
}

export interface CytoscapeEdgeData {
  id: string
  source: string
  target: string
  label: string
  confidence?: number
}

export interface CytoscapeNode {
  data: CytoscapeNodeData
}

export interface CytoscapeEdge {
  data: CytoscapeEdgeData
}

export interface GraphData {
  nodes: CytoscapeNode[]
  edges: CytoscapeEdge[]
}
