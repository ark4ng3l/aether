import React, { useState, useEffect, useMemo } from 'react'
import {
  Wrench,
  Search,
  Plus,
  Sparkles,
  Play,
  Terminal,
  Shield,
  RefreshCw,
  SlidersHorizontal,
} from 'lucide-react'
import { ToolDefinition } from '../../types/api'
import { api } from '../../api/endpoints'
import { ToolCard } from './ToolCard'
import { CodeReviewModal } from './CodeReviewModal'
import { EmptyState } from '../../components/ui/EmptyState'

export const ArsenalTab: React.FC = () => {
  const [tools, setTools] = useState<ToolDefinition[]>([])
  const [stagedTools, setStagedTools] = useState<ToolDefinition[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [selectedToolForCode, setSelectedToolForCode] = useState<ToolDefinition | null>(null)
  const [selectedToolForTest, setSelectedToolForTest] = useState<ToolDefinition | null>(null)
  const [testParams, setTestParams] = useState<Record<string, string>>({})
  const [testResult, setTestResult] = useState<any>(null)
  const [isTesting, setIsTesting] = useState(false)

  // Tool synthesis state
  const [synthesisPrompt, setSynthesisPrompt] = useState('')
  const [isSynthesizing, setIsSynthesizing] = useState(false)

  const fetchTools = async () => {
    setIsLoading(true)
    try {
      const [allTools, staged] = await Promise.all([
        api.listTools(),
        api.listStagedTools().catch(() => ({ staged_tools: [] })),
      ])
      setTools(allTools)
      setStagedTools(staged.staged_tools || [])
    } catch (err) {
      console.error('Failed to fetch tools:', err)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchTools()
  }, [])

  // Categories list
  const categories = useMemo(() => {
    const set = new Set(tools.map((t) => t.category || 'General'))
    return ['all', ...Array.from(set).sort()]
  }, [tools])

  // Filtered tools
  const filteredTools = useMemo(() => {
    return tools.filter((tool) => {
      if (selectedCategory !== 'all' && (tool.category || 'General') !== selectedCategory) {
        return false
      }
      if (searchQuery) {
        const q = searchQuery.toLowerCase()
        const matchName = tool.name.toLowerCase().includes(q)
        const matchDesc = tool.description.toLowerCase().includes(q)
        if (!matchName && !matchDesc) return false
      }
      return true
    })
  }, [tools, selectedCategory, searchQuery])

  const handleSynthesize = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!synthesisPrompt.trim() || isSynthesizing) return
    setIsSynthesizing(true)
    try {
      await api.synthesizeTool(synthesisPrompt, false)
      setSynthesisPrompt('')
      await fetchTools()
    } catch (err) {
      console.error('Synthesis failed:', err)
    } finally {
      setIsSynthesizing(false)
    }
  }

  const handleRunIsolatedTest = async () => {
    if (!selectedToolForTest || isTesting) return
    setIsTesting(true)
    setTestResult(null)
    try {
      const res = await api.executeTool(selectedToolForTest.name, testParams)
      setTestResult(res)
    } catch (err: any) {
      setTestResult({ success: false, error: err.message })
    } finally {
      setIsTesting(false)
    }
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-bg-canvas select-none">
      {/* Top Header & Search Bar */}
      <div className="p-3 bg-bg-surface border-b border-border-subtle flex flex-wrap items-center justify-between gap-3 shrink-0">
        <div className="flex items-center gap-2 flex-1 max-w-md">
          <div className="relative flex-1">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-text-tertiary" strokeWidth={1.5} />
            <input
              type="text"
              placeholder="Search tools by capability or name..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full h-8 pl-8 pr-3 text-2xs bg-bg-canvas border border-border-subtle rounded text-text-primary placeholder:text-text-tertiary focus:border-accent focus:ring-0"
            />
          </div>
        </div>

        {/* Category Tabs */}
        <div className="flex items-center gap-1 overflow-x-auto scrollbar-none">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-2.5 py-1 text-2xs font-medium rounded capitalize transition-colors ${
                selectedCategory === cat
                  ? 'bg-accent-subtle text-accent border border-accent/20'
                  : 'text-text-tertiary hover:text-text-secondary'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        <button
          onClick={fetchTools}
          className="p-1.5 rounded text-text-tertiary hover:text-text-primary hover:bg-bg-canvas transition-colors"
          title="Refresh tools"
        >
          <RefreshCw className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Main Grid View */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {/* AI Synthesis Prompt Bar */}
        <div className="p-4 rounded-xl border border-accent/20 bg-bg-surface shadow-sm">
          <div className="flex items-center gap-2 mb-2">
            <Sparkles className="w-4 h-4 text-accent" />
            <h3 className="text-xs font-bold text-text-primary">Autonomous Tool Synthesizer</h3>
          </div>
          <p className="text-2xs text-text-secondary mb-3">
            Prompt the LLM agent to write, AST-verify, and register a new Python reconnaissance tool in the sandbox.
          </p>
          <form onSubmit={handleSynthesize} className="flex gap-2">
            <input
              type="text"
              placeholder="e.g. Scrape pastebin mentions or query crt.sh JSON endpoint for wildcard certificates..."
              value={synthesisPrompt}
              onChange={(e) => setSynthesisPrompt(e.target.value)}
              className="flex-1 h-8 px-3 text-2xs bg-bg-canvas border border-border-subtle rounded text-text-primary placeholder:text-text-tertiary focus:border-accent focus:ring-0"
            />
            <button
              type="submit"
              disabled={isSynthesizing || !synthesisPrompt.trim()}
              className="px-4 py-1.5 text-2xs font-medium text-white bg-accent hover:bg-accent-hover rounded disabled:opacity-50 transition-colors shrink-0 flex items-center gap-1.5"
            >
              <Sparkles className="w-3 h-3" />
              {isSynthesizing ? 'Synthesizing...' : 'Synthesize Tool'}
            </button>
          </form>
        </div>

        {/* Staged Tools Awaiting Review */}
        {stagedTools.length > 0 && (
          <div>
            <h3 className="text-xs font-bold text-status-plausible mb-2 flex items-center gap-1.5">
              <Shield className="w-3.5 h-3.5" /> Staged Tools Awaiting Authorization ({stagedTools.length})
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {stagedTools.map((tool) => (
                <div
                  key={tool.name}
                  className="p-3 rounded-lg border border-status-plausible/30 bg-status-plausible/5 space-y-2"
                >
                  <h4 className="text-xs font-bold text-text-primary font-mono-data">{tool.name}</h4>
                  <p className="text-2xs text-text-secondary">{tool.description}</p>
                  <button
                    onClick={() => setSelectedToolForCode(tool)}
                    className="w-full py-1 text-2xs font-medium rounded bg-status-plausible text-white hover:bg-status-plausible/90 transition-colors"
                  >
                    Review AST & Authorize
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Available Tools Grid */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-xs font-bold text-text-primary uppercase tracking-wider">
              Registered Arsenal ({filteredTools.length})
            </h3>
          </div>

          {filteredTools.length === 0 ? (
            <EmptyState
              icon={Wrench}
              title="No tools found"
              description="No tools match the selected filters."
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {filteredTools.map((tool) => (
                <ToolCard
                  key={tool.name}
                  tool={tool}
                  onOpenLiveTester={(t) => {
                    setSelectedToolForTest(t)
                    const initial: Record<string, string> = {}
                    if (t.params) {
                      Object.keys(t.params).forEach((k) => (initial[k] = ''))
                    }
                    setTestParams(initial)
                    setTestResult(null)
                  }}
                  onReviewCode={(t) => setSelectedToolForCode(t)}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Code Review Modal */}
      {selectedToolForCode && (
        <CodeReviewModal
          tool={selectedToolForCode}
          isOpen={true}
          onClose={() => setSelectedToolForCode(null)}
          onApproved={fetchTools}
          onRejected={fetchTools}
        />
      )}

      {/* Isolated Tool Tester Drawer */}
      {selectedToolForTest && (
        <div className="fixed inset-y-0 right-0 z-50 w-96 bg-bg-surface border-l border-border-subtle shadow-overlay flex flex-col animate-slide-up select-text">
          <div className="p-3.5 border-b border-border-subtle flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Terminal className="w-4 h-4 text-accent" />
              <h3 className="text-xs font-bold text-text-primary font-mono-data">
                Test: {selectedToolForTest.name}
              </h3>
            </div>
            <button
              onClick={() => setSelectedToolForTest(null)}
              className="text-text-tertiary hover:text-text-primary"
            >
              ✕
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4 text-2xs">
            <p className="text-text-secondary leading-relaxed">
              {selectedToolForTest.description}
            </p>

            <div className="space-y-2">
              <span className="font-semibold text-text-tertiary uppercase tracking-wider block">
                Parameters
              </span>
              {Object.keys(selectedToolForTest.params || {}).length === 0 ? (
                <p className="text-text-tertiary italic">No parameters required</p>
              ) : (
                Object.keys(selectedToolForTest.params).map((key) => (
                  <div key={key} className="space-y-1">
                    <label className="text-text-secondary font-mono-data block">{key}:</label>
                    <input
                      type="text"
                      value={testParams[key] || ''}
                      onChange={(e) =>
                        setTestParams({ ...testParams, [key]: e.target.value })
                      }
                      placeholder={`Enter ${key}...`}
                      className="w-full h-7 px-2 text-2xs bg-bg-canvas border border-border-subtle rounded text-text-primary font-mono-data"
                    />
                  </div>
                ))
              )}
            </div>

            <button
              onClick={handleRunIsolatedTest}
              disabled={isTesting}
              className="w-full py-1.5 rounded text-2xs font-medium text-white bg-accent hover:bg-accent-hover disabled:opacity-50 transition-colors flex items-center justify-center gap-1.5"
            >
              <Play className="w-3 h-3" />
              {isTesting ? 'Executing in Sandbox...' : 'Run Isolated Test'}
            </button>

            {testResult && (
              <div className="space-y-1.5">
                <span className="font-semibold text-text-tertiary uppercase tracking-wider block">
                  Execution Output
                </span>
                <pre className="p-3 rounded-lg bg-bg-canvas border border-border-subtle text-[11px] font-mono-data text-text-secondary max-h-64 overflow-y-auto whitespace-pre-wrap">
                  {JSON.stringify(testResult, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
