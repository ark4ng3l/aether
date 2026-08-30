import React, { useState, useRef, useEffect } from 'react'
import { Globe, Check } from 'lucide-react'
import { useLocaleStore } from '../../stores/useLocaleStore'
import { SUPPORTED_LOCALES, SupportedLocale } from '../../i18n/translations'

export const LanguageSelector: React.FC = () => {
  const { locale, setLocale } = useLocaleStore()
  const [isOpen, setIsOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const currentMeta = SUPPORTED_LOCALES.find((l) => l.code === locale) || SUPPORTED_LOCALES[0]

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1.5 px-2 py-1 rounded text-2xs font-medium border border-border-subtle bg-bg-surface hover:border-border-strong text-text-secondary hover:text-text-primary transition-colors duration-120 select-none"
        title="Change Language"
      >
        <Globe className="w-3.5 h-3.5 text-text-tertiary" strokeWidth={1.5} />
        <span>{currentMeta.flag}</span>
        <span className="hidden sm:inline">{currentMeta.nativeName}</span>
      </button>

      {isOpen && (
        <div className="absolute right-0 rtl:right-auto rtl:left-0 mt-1.5 w-36 rounded-md bg-bg-elevated border border-border-strong shadow-xl py-1 z-50 animate-in fade-in zoom-in-95 duration-100">
          {SUPPORTED_LOCALES.map((item) => (
            <button
              key={item.code}
              onClick={() => {
                setLocale(item.code)
                setIsOpen(false)
              }}
              className={`w-full flex items-center justify-between px-3 py-1.5 text-2xs transition-colors duration-100 ${
                locale === item.code
                  ? 'bg-accent/15 text-accent font-semibold'
                  : 'text-text-secondary hover:bg-bg-surface hover:text-text-primary'
              }`}
            >
              <div className="flex items-center gap-2">
                <span>{item.flag}</span>
                <span>{item.nativeName}</span>
              </div>
              {locale === item.code && <Check className="w-3 h-3 text-accent" strokeWidth={2} />}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
