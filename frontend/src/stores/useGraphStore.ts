import { create } from 'zustand'
import { CytoscapeNode, CytoscapeEdge, GraphData } from '../types/graph'
import { Entity } from '../types/api'

interface GraphState {
  nodes: CytoscapeNode[]
  edges: CytoscapeEdge[]
  isolatedNodeId: string | null
  hiddenNodeIds: string[]
  selectedEntity: Entity | null

  setGraphData: (data: GraphData) => void
  addEntityNode: (entity: Entity, isSeed?: boolean) => void
  addRelationshipEdge: (source: string, target: string, label: string) => void
  setIsolatedNodeId: (nodeId: string | null) => void
  toggleHideNode: (nodeId: string) => void
  setSelectedEntity: (entity: Entity | null) => void
  clearGraph: () => void
}

export const useGraphStore = create<GraphState>((set) => ({
  nodes: [],
  edges: [],
  isolatedNodeId: null,
  hiddenNodeIds: [],
  selectedEntity: null,

  setGraphData: (data) =>
    set({
      nodes: data.nodes || [],
      edges: data.edges || [],
      isolatedNodeId: null,
    }),

  addEntityNode: (entity, isSeed = false) => {
    set((state) => {
      if (state.nodes.some((n) => n.data.id === entity.id)) {
        return {
          nodes: state.nodes.map((n) =>
            n.data.id === entity.id
              ? {
                  ...n,
                  data: {
                    ...n.data,
                    confidence: entity.confidence,
                    corroboration_count: entity.corroboration_count,
                    properties: entity.properties,
                    confidence_signals: entity.confidence_signals,
                  },
                }
              : n
          ),
        }
      }

      const label =
        entity.properties?.name ||
        entity.properties?.label ||
        entity.id

      const newNode: CytoscapeNode = {
        data: {
          id: entity.id,
          label: String(label),
          type: entity.type,
          confidence: entity.confidence,
          corroboration_count: entity.corroboration_count || 1,
          properties: entity.properties,
          confidence_signals: entity.confidence_signals,
          is_seed: isSeed,
        },
      }

      return { nodes: [...state.nodes, newNode] }
    })
  },

  addRelationshipEdge: (source, target, label) => {
    set((state) => {
      const edgeId = `${source}->${target}:${label}`
      if (state.edges.some((e) => e.data.id === edgeId)) return state

      const newEdge: CytoscapeEdge = {
        data: {
          id: edgeId,
          source,
          target,
          label,
        },
      }
      return { edges: [...state.edges, newEdge] }
    })
  },

  setIsolatedNodeId: (nodeId) => set({ isolatedNodeId: nodeId }),

  toggleHideNode: (nodeId) => {
    set((state) => ({
      hiddenNodeIds: state.hiddenNodeIds.includes(nodeId)
        ? state.hiddenNodeIds.filter((id) => id !== nodeId)
        : [...state.hiddenNodeIds, nodeId],
    }))
  },

  setSelectedEntity: (entity) => set({ selectedEntity: entity }),

  clearGraph: () => set({ nodes: [], edges: [], isolatedNodeId: null, hiddenNodeIds: [], selectedEntity: null }),
}))
