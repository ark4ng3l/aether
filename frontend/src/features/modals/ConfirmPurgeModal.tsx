import React, { useState } from 'react'
import { AlertTriangle, X, Trash2 } from 'lucide-react'
import { useProjectStore } from '../../stores/useProjectStore'
import { api } from '../../api/endpoints'

export const ConfirmPurgeModal: React.FC = () => {
  const { isPurgeModalOpen, setIsPurgeModalOpen, activeProjectId, activeProject, setProjects, setActiveProjectId } =
    useProjectStore()
  const [isDeleting, setIsDeleting] = useState(false)

  if (!isPurgeModalOpen || !activeProject) return null

  const handleDelete = async () => {
    if (!activeProjectId || isDeleting) return
    setIsDeleting(true)
    try {
      await api.deleteProject(activeProjectId)
      const list = await api.listProjects()
      setProjects(list)
      setActiveProjectId(list.length > 0 ? list[0].id : null)
      setIsPurgeModalOpen(false)
    } catch (err) {
      console.error('Failed to delete project:', err)
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-bg-overlay glass animate-fade-in select-none">
      <div className="bg-bg-surface border border-border-subtle rounded-xl shadow-overlay max-w-sm w-full p-5 space-y-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-status-rejected/10 border border-status-rejected/20 flex items-center justify-center text-status-rejected shrink-0">
            <AlertTriangle className="w-5 h-5" strokeWidth={1.5} />
          </div>
          <div>
            <h3 className="text-sm font-bold text-text-primary">Purge Investigation</h3>
            <p className="text-2xs text-text-tertiary">This action cannot be undone.</p>
          </div>
        </div>

        <p className="text-2xs text-text-secondary leading-relaxed">
          Are you sure you want to permanently delete <strong className="text-text-primary">{activeProject.name}</strong> and all its discovered entity graphs, intelligence dossiers, and timeline logs?
        </p>

        <div className="pt-3 border-t border-border-subtle flex items-center justify-between">
          <button
            onClick={() => setIsPurgeModalOpen(false)}
            className="px-3 py-1.5 text-2xs font-medium text-text-secondary hover:text-text-primary transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleDelete}
            disabled={isDeleting}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded text-2xs font-medium text-white bg-status-rejected hover:bg-status-rejected/90 disabled:opacity-50 transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
            {isDeleting ? 'Deleting...' : 'Delete Project'}
          </button>
        </div>
      </div>
    </div>
  )
}
