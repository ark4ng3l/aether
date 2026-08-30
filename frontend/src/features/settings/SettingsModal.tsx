import React, { useState, useEffect } from 'react'
import {
  Settings,
  X,
  Save,
  CheckCircle2,
  RefreshCw,
  Cpu,
  Eye,
  ShieldAlert,
  Brain,
  Zap,
  Server,
  Sliders,
  Lock,
  Cloud,
  HardDrive,
  Key,
} from 'lucide-react'
import { useProjectStore } from '../../stores/useProjectStore'
import { useAuthStore } from '../../stores/useAuthStore'
import { useLocaleStore } from '../../stores/useLocaleStore'
import { api } from '../../api/endpoints'
import { SettingsData, MetricsData } from '../../types/api'

export const SettingsModal: React.FC = () => {
  const { isSettingsOpen, setIsSettingsOpen } = useProjectStore()
  const { token, updateToken } = useAuthStore()
  const { t } = useLocaleStore()

  const [settings, setSettings] = useState<Partial<SettingsData>>({})
  const [availableModels, setAvailableModels] = useState<string[]>([])
  const [metrics, setMetrics] = useState<MetricsData | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isFetchingModels, setIsFetchingModels] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState(false)

  const provider = settings.LLM_PROVIDER || 'ollama'

  const loadSettingsAndModels = async () => {
    setIsLoading(true)
    try {
      const [res, metricsData] = await Promise.all([
        api.getSettings().catch(() => ({ settings: {} as SettingsData, available_models: [] })),
        api.getMetrics().catch(() => null),
      ])
      setSettings(res.settings || {})
      setAvailableModels(res.available_models || [])
      setMetrics(metricsData)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (!isSettingsOpen) return
    loadSettingsAndModels()
  }, [isSettingsOpen])

  const handleRefreshModels = async () => {
    setIsFetchingModels(true)
    try {
      const res = await api.getSettings()
      setAvailableModels(res.available_models || [])
    } catch (err) {
      console.error('Failed to refresh models:', err)
    } finally {
      setIsFetchingModels(false)
    }
  }

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

  const renderModelField = (
    key: keyof SettingsData,
    label: string,
    description: string,
    icon: React.ElementType,
    badgeColor: string = 'text-accent'
  ) => {
    const IconComp = icon
    const currentValue = (settings[key] as string) || ''
    const isOllama = provider === 'ollama'

    return (
      <div className="bg-bg-canvas p-3 rounded-xl border border-border-subtle hover:border-border-strong transition-all">
        <div className="flex items-center justify-between mb-1.5">
          <label className="flex items-center gap-1.5 text-text-primary font-medium text-2xs">
            <IconComp className={`w-3.5 h-3.5 ${badgeColor}`} />
            {label}
          </label>
          {isOllama && availableModels.length > 0 && (
            <span className="text-[10px] text-text-tertiary font-mono">
              {availableModels.includes(currentValue) ? (
                <span className="text-status-confirmed flex items-center gap-1 font-sans">
                  <span className="w-1.5 h-1.5 rounded-full bg-status-confirmed inline-block" /> Installed
                </span>
              ) : (
                <span className="text-amber-400/80 font-sans">Custom/Remote</span>
              )}
            </span>
          )}
        </div>

        <p className="text-[11px] text-text-tertiary mb-2">{description}</p>

        <div className="space-y-1.5">
          {/* Quick Selector Dropdown if Ollama models exist */}
          {isOllama && availableModels.length > 0 && (
            <select
              value={availableModels.includes(currentValue) ? currentValue : ''}
              onChange={(e) => {
                if (e.target.value) {
                  setSettings({ ...settings, [key]: e.target.value })
                }
              }}
              className="w-full h-8 px-2 bg-bg-surface border border-border-subtle hover:border-accent/40 rounded-lg text-text-primary text-2xs outline-none focus:border-accent cursor-pointer transition-colors"
            >
              <option value="" disabled>
                -- Select from {availableModels.length} detected Ollama models --
              </option>
              {availableModels.map((m) => (
                <option key={m} value={m}>
                  📦 {m}
                </option>
              ))}
            </select>
          )}

          {/* Text Input for Custom or Exact Identifier */}
          <div className="relative">
            <input
              type="text"
              list={isOllama ? 'ollama-models-datalist' : undefined}
              value={currentValue}
              onChange={(e) => setSettings({ ...settings, [key]: e.target.value })}
              placeholder={
                isOllama
                  ? 'e.g. gemma2:9b or hf.co/...'
                  : 'e.g. gpt-4o, claude-3-5-sonnet, deepseek-chat, mistral-large'
              }
              className="w-full h-8 px-2.5 bg-bg-surface border border-border-subtle focus:border-accent rounded-lg text-text-primary font-mono text-[11px] outline-none transition-colors"
            />
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-bg-overlay glass animate-fade-in select-none">
      <div className="bg-bg-surface border border-border-subtle rounded-2xl shadow-overlay max-w-3xl w-full max-h-[90vh] flex flex-col overflow-hidden">
        {/* Datalist for global autocompletion */}
        <datalist id="ollama-models-datalist">
          {availableModels.map((m) => (
            <option key={m} value={m} />
          ))}
        </datalist>

        {/* Header */}
        <div className="p-4 sm:p-5 border-b border-border-subtle flex items-center justify-between bg-bg-surface">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-accent-subtle border border-accent/20 flex items-center justify-center text-accent shadow-inner">
              <Settings className="w-5 h-5" strokeWidth={1.75} />
            </div>
            <div>
              <h3 className="text-sm font-bold text-text-primary tracking-tight">
                {t('settings.title', 'System Settings & Neural Model Matrix')}
              </h3>
              <p className="text-2xs text-text-tertiary">
                {t('settings.subtitle', 'Configure local Ollama models, custom OpenAI-compatible cloud APIs, and reasoning parameters')}
              </p>
            </div>
          </div>
          <button
            onClick={() => setIsSettingsOpen(false)}
            className="p-1.5 rounded-lg text-text-tertiary hover:text-text-primary hover:bg-bg-canvas transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form Body */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6 text-2xs select-text scrollbar-thin">
          {/* Provider Selector Switcher */}
          <div className="space-y-3">
            <label className="text-text-primary font-semibold text-xs block">
              LLM Inference Engine Provider
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setSettings({ ...settings, LLM_PROVIDER: 'ollama' })}
                className={`p-3 rounded-xl border flex items-center gap-3 text-left transition-all ${
                  provider === 'ollama'
                    ? 'border-accent bg-accent/10 shadow-sm shadow-accent/10'
                    : 'border-border-subtle bg-bg-canvas hover:border-border-strong text-text-secondary'
                }`}
              >
                <div
                  className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                    provider === 'ollama' ? 'bg-accent text-white' : 'bg-bg-surface text-text-tertiary'
                  }`}
                >
                  <HardDrive className="w-4 h-4" />
                </div>
                <div>
                  <div className="font-semibold text-text-primary text-2xs">Local Ollama Engine</div>
                  <div className="text-[11px] text-text-tertiary">VRAM-arbitrated uncensored local models</div>
                </div>
              </button>

              <button
                type="button"
                onClick={() => setSettings({ ...settings, LLM_PROVIDER: 'openai_compatible' })}
                className={`p-3 rounded-xl border flex items-center gap-3 text-left transition-all ${
                  provider === 'openai_compatible'
                    ? 'border-accent bg-accent/10 shadow-sm shadow-accent/10'
                    : 'border-border-subtle bg-bg-canvas hover:border-border-strong text-text-secondary'
                }`}
              >
                <div
                  className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                    provider === 'openai_compatible' ? 'bg-accent text-white' : 'bg-bg-surface text-text-tertiary'
                  }`}
                >
                  <Cloud className="w-4 h-4" />
                </div>
                <div>
                  <div className="font-semibold text-text-primary text-2xs">Custom / Cloud API</div>
                  <div className="text-[11px] text-text-tertiary">OpenAI, vLLM, OpenRouter, DeepSeek, Groq</div>
                </div>
              </button>
            </div>
          </div>

          {/* Connection Endpoint Details */}
          {provider === 'ollama' ? (
            <div className="space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-border-subtle">
                <div className="flex items-center gap-2">
                  <Server className="w-4 h-4 text-purple-400" />
                  <span className="font-semibold text-text-primary text-xs">
                    {t('settings.neuralSection', 'Local Ollama & Neural Models')}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={`text-[11px] px-2.5 py-0.5 rounded-full font-mono flex items-center gap-1.5 border ${
                      availableModels.length > 0
                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                        : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                    }`}
                  >
                    <span
                      className={`w-1.5 h-1.5 rounded-full ${
                        availableModels.length > 0 ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'
                      }`}
                    />
                    {availableModels.length > 0
                      ? `${availableModels.length} Local Models Detected`
                      : 'Ollama Offline / No Models'}
                  </span>
                  <button
                    onClick={handleRefreshModels}
                    disabled={isFetchingModels}
                    title="Refresh models from Ollama"
                    className="flex items-center gap-1 px-2.5 py-1 text-[11px] bg-bg-canvas hover:bg-bg-surface-raised border border-border-strong rounded-lg text-text-secondary hover:text-text-primary transition-colors disabled:opacity-50 shadow-xs"
                  >
                    <RefreshCw className={`w-3 h-3 ${isFetchingModels ? 'animate-spin text-accent' : ''}`} />
                    <span>Fetch Models</span>
                  </button>
                </div>
              </div>

              {/* Ollama Base URL */}
              <div className="bg-bg-canvas p-3 rounded-xl border border-border-subtle">
                <label className="text-text-secondary block mb-1 font-medium">{t('settings.ollamaUrl', 'Ollama Base URL')}</label>
                <input
                  type="text"
                  value={settings.OLLAMA_BASE_URL || ''}
                  onChange={(e) => setSettings({ ...settings, OLLAMA_BASE_URL: e.target.value })}
                  placeholder="http://localhost:11434"
                  className="w-full h-8 px-2.5 bg-bg-surface border border-border-subtle rounded-lg text-text-primary font-mono text-[11px] outline-none focus:border-accent"
                />
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center gap-2 pb-2 border-b border-border-subtle">
                <Cloud className="w-4 h-4 text-cyan-400" />
                <span className="font-semibold text-text-primary text-xs">
                  Custom OpenAI-Compatible API Configuration
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                <div className="bg-bg-canvas p-3 rounded-xl border border-border-subtle">
                  <label className="text-text-secondary block mb-1 font-medium">Custom API Base URL</label>
                  <input
                    type="text"
                    value={settings.CUSTOM_API_BASE_URL || ''}
                    onChange={(e) => setSettings({ ...settings, CUSTOM_API_BASE_URL: e.target.value })}
                    placeholder="https://api.openai.com/v1 or https://openrouter.ai/api/v1"
                    className="w-full h-8 px-2.5 bg-bg-surface border border-border-subtle rounded-lg text-text-primary font-mono text-[11px] outline-none focus:border-accent"
                  />
                </div>

                <div className="bg-bg-canvas p-3 rounded-xl border border-border-subtle">
                  <label className="text-text-secondary flex items-center gap-1 mb-1 font-medium">
                    <Key className="w-3 h-3 text-amber-400" /> API Key / Bearer Token
                  </label>
                  <input
                    type="password"
                    value={settings.CUSTOM_API_KEY || ''}
                    onChange={(e) => setSettings({ ...settings, CUSTOM_API_KEY: e.target.value })}
                    placeholder="sk-..."
                    className="w-full h-8 px-2.5 bg-bg-surface border border-border-subtle rounded-lg text-text-primary font-mono text-[11px] outline-none focus:border-accent"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Neural Role Selectors Grid */}
          <div className="space-y-3">
            <span className="font-semibold text-accent uppercase tracking-wider block text-xs">
              Model Mapping Matrix
            </span>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
              {renderModelField(
                'MODEL_FAST',
                'Fast Tactical Planner & Router',
                'High-speed model for decomposing goals and selecting tools',
                Zap,
                'text-amber-400'
              )}

              {renderModelField(
                'MODEL_AGGRESSIVE_FAST',
                'Aggressive Parallel Tool Caller',
                'Executes parallel tool calls and JSON parameter formatting',
                Cpu,
                'text-purple-400'
              )}

              {renderModelField(
                'MODEL_CRITIC',
                'Red-Team Adversarial Critic',
                'Verifies findings, evaluates evidence confidence, and refutes false positives',
                ShieldAlert,
                'text-rose-400'
              )}

              {renderModelField(
                'MODEL_VLM',
                'Multimodal Vision & OCR (VLM)',
                'Visual forensics, OCR, scene analysis, and satellite geolocation',
                Eye,
                'text-cyan-400'
              )}

              {renderModelField(
                'MODEL_DEEP',
                'Deep Abductive Reasoning & Dossier',
                'Synthesizes high-level hypotheses and composes executive intelligence dossiers',
                Brain,
                'text-emerald-400'
              )}

              {renderModelField(
                'MODEL_DEEP_FALLBACK',
                'Heavy Reasoning Fallback',
                'Secondary deep model for complex multi-hop graph correlations',
                Server,
                'text-blue-400'
              )}
            </div>
          </div>

          {/* Reasoning & Investigation Thresholds */}
          <div className="space-y-3 pt-4 border-t border-border-subtle">
            <div className="flex items-center gap-2 mb-2">
              <Sliders className="w-4 h-4 text-accent" />
              <span className="font-semibold text-text-primary text-xs">
                {t('settings.reasoningSection', 'Cognitive Parameters & Thresholds')}
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="bg-bg-canvas p-3 rounded-xl border border-border-subtle">
                <label className="text-text-secondary block mb-1 font-medium">
                  {t('settings.confidenceThreshold', 'Confidence Threshold')}
                </label>
                <input
                  type="number"
                  step="0.05"
                  min="0"
                  max="1"
                  value={settings.ENTITY_CONFIDENCE_THRESHOLD ?? 0.75}
                  onChange={(e) =>
                    setSettings({ ...settings, ENTITY_CONFIDENCE_THRESHOLD: parseFloat(e.target.value) })
                  }
                  className="w-full h-8 px-2.5 bg-bg-surface border border-border-subtle rounded-lg text-text-primary font-mono text-[11px] outline-none focus:border-accent"
                />
              </div>

              <div className="bg-bg-canvas p-3 rounded-xl border border-border-subtle">
                <label className="text-text-secondary block mb-1 font-medium">
                  {t('settings.searchDepth', 'Max Search Depth')}
                </label>
                <input
                  type="number"
                  min="1"
                  max="50"
                  value={settings.MAX_SEARCH_DEPTH ?? 30}
                  onChange={(e) =>
                    setSettings({ ...settings, MAX_SEARCH_DEPTH: parseInt(e.target.value, 10) })
                  }
                  className="w-full h-8 px-2.5 bg-bg-surface border border-border-subtle rounded-lg text-text-primary font-mono text-[11px] outline-none focus:border-accent"
                />
              </div>

              <div className="bg-bg-canvas p-3 rounded-xl border border-border-subtle">
                <label className="text-text-secondary block mb-1 font-medium">
                  {t('settings.hypothesisLimit', 'Hypothesis Limit')}
                </label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  value={settings.HYPOTHESIS_RECURSION_LIMIT ?? 5}
                  onChange={(e) =>
                    setSettings({ ...settings, HYPOTHESIS_RECURSION_LIMIT: parseInt(e.target.value, 10) })
                  }
                  className="w-full h-8 px-2.5 bg-bg-surface border border-border-subtle rounded-lg text-text-primary font-mono text-[11px] outline-none focus:border-accent"
                />
              </div>
            </div>
          </div>

          {/* Security & Authentication */}
          <div className="space-y-3 pt-4 border-t border-border-subtle">
            <div className="flex items-center gap-2 mb-2">
              <Lock className="w-4 h-4 text-amber-400" />
              <span className="font-semibold text-text-primary text-xs">
                {t('settings.securitySection', 'Security & Access Control')}
              </span>
            </div>
            <div className="p-3.5 rounded-xl border border-border-subtle bg-bg-canvas flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <p className="font-medium text-text-primary">{t('settings.bearerToken', 'Bearer Authentication Token')}</p>
                <p className="text-text-tertiary text-[11px] font-mono truncate max-w-sm">
                  {token ? `${token.slice(0, 18)}••••••••••••••••••••••••` : 'No token active'}
                </p>
              </div>
              <button
                onClick={handleRegenerateToken}
                className="px-3 py-1.5 text-2xs font-medium text-status-rejected border border-status-rejected/30 hover:bg-status-rejected/10 rounded-lg transition-colors shrink-0"
              >
                {t('settings.regenerateToken', 'Regenerate Token')}
              </button>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-border-subtle bg-bg-canvas flex items-center justify-between">
          <button
            onClick={() => setIsSettingsOpen(false)}
            className="px-3.5 py-1.5 text-2xs font-medium text-text-secondary hover:text-text-primary bg-bg-surface border border-border-subtle rounded-lg transition-colors"
          >
            {t('action.close', 'Close')}
          </button>
          <div className="flex items-center gap-2.5">
            {saveSuccess && (
              <span className="flex items-center gap-1 text-2xs text-status-confirmed animate-fade-in font-medium">
                <CheckCircle2 className="w-3.5 h-3.5" /> {t('action.saved', 'Settings Saved Successfully!')}
              </span>
            )}
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="flex items-center gap-1.5 px-4 py-1.5 text-2xs font-semibold text-white bg-gradient-to-r from-accent to-blue-600 hover:brightness-110 rounded-lg transition-all disabled:opacity-50 shadow-md shadow-accent/20"
            >
              <Save className="w-3.5 h-3.5" />
              {isSaving ? t('action.saving', 'Saving...') : t('settings.saveBtn', 'Save Settings')}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
