import React, { useState, useEffect } from 'react'
import {
  Settings,
  X,
  Save,
  Key,
  Cpu,
  Sliders,
  Shield,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react'
import { useProjectStore } from '../../stores/useProjectStore'
import { useAuthStore } from '../../stores/useAuthStore'
import { api } from '../../api/endpoints'
import { SettingsData, MetricsData } from '../../types/api'

export const SettingsModal: React.FC = () => {
  const { isSettingsOpen, setIsSettingsOpen } = useProjectStore()
  const { token, updateToken } = useAuthStore()

  const [settings, setSettings] = useState<Partial<SettingsData>>({})
  const [metrics, setMetrics] = useState<MetricsData | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState(false)

  useEffect(() => {
    if (!isSettingsOpen) return
    setIsLoading(true)
    Promise.all([
      api.getSettings().catch(() => ({})),
      api.getMetrics().catch(() => null),
    ])
      .then(([settingsData, metricsData]) => {
        setSettings(settingsData as any)
        setMetrics(metricsData)
      })
      .finally(() => setIsLoading(false))
  }, [isSettingsOpen])

  if (!isSettingsOpen) return null

  const handleSave = async () => {
    setIsSaving(true)
    setSaveSuccess(false)
    try {
      await api.updateSettings(settings)
      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 2500)
    } catch (err) {
      console.error('Failed to save settings:', err)
    } finally {
      setIsSaving(false)
    }
  }

  const handleRegenerateToken = async () => {
    if (!window.confirm('Regenerate authentication token? All current browser sessions will need the new token.')) {
      return
    }
    try {
      const res = await api.regenerateToken()
      if (res.token) {
        updateToken(res.token)
        alert('Authentication token regenerated successfully.')
      }
    } catch (err) {
      console.error('Failed to regenerate token:', err)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-bg-overlay glass animate-fade-in select-none">
      <div className="bg-bg-surface border border-border-subtle rounded-xl shadow-overlay max-w-2xl w-full max-h-[90vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b border-border-subtle flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-accent/10 flex items-center justify-center text-accent">
              <Settings className="w-4 h-4" strokeWidth={1.5} />
            </div>
            <div>
              <h3 className="text-sm font-bold text-text-primary">System Settings & Neural Config</h3>
              <p className="text-2xs text-text-tertiary">Configure local Ollama models, VRAM arbitration, and security parameters</p>
            </div>
          </div>
          <button
            onClick={() => setIsSettingsOpen(false)}
            className="p-1 rounded text-text-tertiary hover:text-text-primary transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form Body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-5 text-2xs select-text">
          {/* LLM & Neural Model Mapping */}
          <div className="space-y-3">
            <span className="font-semibold text-accent uppercase tracking-wider block">
              Local Ollama & Neural Models
            </span>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="text-text-secondary block mb-1">Ollama Base URL</label>
                <input
                  type="text"
                  value={settings.OLLAMA_BASE_URL || ''}
                  onChange={(e) => setSettings({ ...settings, OLLAMA_BASE_URL: e.target.value })}
                  className="w-full h-8 px-2.5 bg-bg-canvas border border-border-subtle rounded text-text-primary font-mono-data"
                />
              </div>
              <div>
                <label className="text-text-secondary block mb-1">Fast Model (Planner / Extractor)</label>
                <input
                  type="text"
                  value={settings.MODEL_FAST || ''}
                  onChange={(e) => setSettings({ ...settings, MODEL_FAST: e.target.value })}
                  className="w-full h-8 px-2.5 bg-bg-canvas border border-border-subtle rounded text-text-primary font-mono-data"
                />
              </div>
              <div>
                <label className="text-text-secondary block mb-1">Critic Model (Adversarial Refuter)</label>
                <input
                  type="text"
                  value={settings.MODEL_CRITIC || ''}
                  onChange={(e) => setSettings({ ...settings, MODEL_CRITIC: e.target.value })}
                  className="w-full h-8 px-2.5 bg-bg-canvas border border-border-subtle rounded text-text-primary font-mono-data"
                />
              </div>
              <div>
                <label className="text-text-secondary block mb-1">Vision VLM Model (OCR / Image OSINT)</label>
                <input
                  type="text"
                  value={settings.MODEL_VLM || ''}
                  onChange={(e) => setSettings({ ...settings, MODEL_VLM: e.target.value })}
                  className="w-full h-8 px-2.5 bg-bg-canvas border border-border-subtle rounded text-text-primary font-mono-data"
                />
              </div>
            </div>
          </div>

          {/* Reasoning & Investigation Thresholds */}
          <div className="space-y-3 pt-3 border-t border-border-subtle">
            <span className="font-semibold text-accent uppercase tracking-wider block">
              Cognitive Parameters & Thresholds
            </span>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div>
                <label className="text-text-secondary block mb-1">Confidence Threshold (0-1)</label>
                <input
                  type="number"
                  step="0.05"
                  min="0"
                  max="1"
                  value={settings.ENTITY_CONFIDENCE_THRESHOLD ?? 0.65}
                  onChange={(e) =>
                    setSettings({ ...settings, ENTITY_CONFIDENCE_THRESHOLD: parseFloat(e.target.value) })
                  }
                  className="w-full h-8 px-2.5 bg-bg-canvas border border-border-subtle rounded text-text-primary font-mono-data"
                />
              </div>
              <div>
                <label className="text-text-secondary block mb-1">Max Search Depth</label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  value={settings.MAX_SEARCH_DEPTH ?? 3}
                  onChange={(e) =>
                    setSettings({ ...settings, MAX_SEARCH_DEPTH: parseInt(e.target.value, 10) })
                  }
                  className="w-full h-8 px-2.5 bg-bg-canvas border border-border-subtle rounded text-text-primary font-mono-data"
                />
              </div>
              <div>
                <label className="text-text-secondary block mb-1">Hypothesis Limit</label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  value={settings.HYPOTHESIS_RECURSION_LIMIT ?? 3}
                  onChange={(e) =>
                    setSettings({ ...settings, HYPOTHESIS_RECURSION_LIMIT: parseInt(e.target.value, 10) })
                  }
                  className="w-full h-8 px-2.5 bg-bg-canvas border border-border-subtle rounded text-text-primary font-mono-data"
                />
              </div>
            </div>
          </div>

          {/* Security & Authentication */}
          <div className="space-y-3 pt-3 border-t border-border-subtle">
            <span className="font-semibold text-accent uppercase tracking-wider block">
              Security & Access Control
            </span>
            <div className="p-3 rounded-lg border border-border-subtle bg-bg-canvas flex items-center justify-between">
              <div>
                <p className="font-medium text-text-primary">Bearer Authentication Token</p>
                <p className="text-text-tertiary text-[11px] font-mono-data truncate max-w-sm">
                  {token ? `${token.slice(0, 16)}...` : 'No token active'}
                </p>
              </div>
              <button
                onClick={handleRegenerateToken}
                className="px-2.5 py-1 text-2xs font-medium text-status-rejected border border-status-rejected/30 hover:bg-status-rejected/10 rounded transition-colors"
              >
                Regenerate Token
              </button>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-border-subtle bg-bg-canvas flex items-center justify-between">
          <button
            onClick={() => setIsSettingsOpen(false)}
            className="px-3 py-1.5 text-2xs font-medium text-text-secondary hover:text-text-primary transition-colors"
          >
            Close
          </button>
          <div className="flex items-center gap-2">
            {saveSuccess && (
              <span className="flex items-center gap-1 text-2xs text-status-confirmed">
                <CheckCircle2 className="w-3.5 h-3.5" /> Saved
              </span>
            )}
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="flex items-center gap-1.5 px-4 py-1.5 text-2xs font-medium text-white bg-accent hover:bg-accent-hover rounded transition-colors disabled:opacity-50"
            >
              <Save className="w-3.5 h-3.5" />
              {isSaving ? 'Saving...' : 'Save Settings'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
