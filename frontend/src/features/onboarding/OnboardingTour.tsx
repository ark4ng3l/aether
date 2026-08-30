import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Sparkles, ArrowRight, Check, X, Shield, GitFork, Command } from 'lucide-react'
import { Kbd } from '../../components/ui/Kbd'

const TOUR_STORAGE_KEY = 'aether_onboarding_completed'

const tourSteps = [
  {
    title: 'Initialize Target Reconnaissance',
    description:
      'Start an investigation by providing a domain, IP address, organization name, or email. The agent coordinates 24+ passive tools automatically.',
    icon: Shield,
  },
  {
    title: 'Interactive Multi-Hop Graph',
    description:
      'Explore discovered infrastructure, corroborating sources, and confidence signals with Cytoscape/fcose force layout. Click any node for full lineage.',
    icon: GitFork,
  },
  {
    title: 'Keyboard-First Command Palette',
    description:
      'Press ⌘K / Ctrl+K anywhere to instantly jump to entities, run tools, toggle themes, or switch investigations without lifting your hands from the keyboard.',
    icon: Command,
    shortcut: '⌘K',
  },
]

export const OnboardingTour: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false)
  const [currentStep, setCurrentStep] = useState(0)

  useEffect(() => {
    const completed = localStorage.getItem(TOUR_STORAGE_KEY)
    if (!completed) {
      setIsOpen(true)
    }
  }, [])

  const handleNext = () => {
    if (currentStep < tourSteps.length - 1) {
      setCurrentStep((prev) => prev + 1)
    } else {
      handleComplete()
    }
  }

  const handleComplete = () => {
    localStorage.setItem(TOUR_STORAGE_KEY, 'true')
    setIsOpen(false)
  }

  if (!isOpen) return null

  const step = tourSteps[currentStep]
  const Icon = step.icon

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-bg-overlay glass animate-fade-in select-none">
        <motion.div
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.96 }}
          transition={{ duration: 0.15 }}
          className="bg-bg-surface border border-border-subtle rounded-xl shadow-overlay max-w-md w-full p-6 space-y-4"
        >
          {/* Top Bar */}
          <div className="flex items-center justify-between">
            <span className="text-2xs font-semibold text-accent uppercase tracking-wider flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5" /> Welcome to AETHER v3 · Step {currentStep + 1} of {tourSteps.length}
            </span>
            <button
              onClick={handleComplete}
              className="text-text-tertiary hover:text-text-primary transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Icon & Content */}
          <div className="flex items-start gap-4">
            <div className="w-10 h-10 rounded-xl bg-accent-subtle border border-accent/20 flex items-center justify-center text-accent shrink-0">
              <Icon className="w-5 h-5" strokeWidth={1.5} />
            </div>
            <div className="space-y-1.5 flex-1">
              <h3 className="text-sm font-bold text-text-primary">{step.title}</h3>
              <p className="text-2xs text-text-secondary leading-relaxed">{step.description}</p>
              {step.shortcut && (
                <div className="pt-1">
                  <Kbd>{step.shortcut}</Kbd>
                </div>
              )}
            </div>
          </div>

          {/* Stepper Dots & Action */}
          <div className="pt-4 border-t border-border-subtle flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              {tourSteps.map((_, i) => (
                <span
                  key={i}
                  className={`w-2 h-2 rounded-full transition-all ${
                    i === currentStep ? 'bg-accent w-4' : 'bg-border-subtle'
                  }`}
                />
              ))}
            </div>

            <button
              onClick={handleNext}
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded text-2xs font-medium text-white bg-accent hover:bg-accent-hover transition-colors"
            >
              {currentStep === tourSteps.length - 1 ? (
                <>
                  <Check className="w-3.5 h-3.5" /> Get Started
                </>
              ) : (
                <>
                  Next <ArrowRight className="w-3.5 h-3.5" />
                </>
              )}
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  )
}
