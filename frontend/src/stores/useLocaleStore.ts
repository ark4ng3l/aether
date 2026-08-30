import { create } from 'zustand'
import { SupportedLocale, SUPPORTED_LOCALES, translations } from '../i18n/translations'

interface LocaleState {
  locale: SupportedLocale
  dir: 'ltr' | 'rtl'
  setLocale: (locale: SupportedLocale) => void
  t: (key: string, defaultText?: string) => string
}

const getInitialLocale = (): SupportedLocale => {
  try {
    const saved = localStorage.getItem('aether_locale') as SupportedLocale
    if (saved && ['en', 'fa', 'ru', 'zh'].includes(saved)) {
      return saved
    }
  } catch {}
  return 'en'
}

const applyHtmlAttributes = (locale: SupportedLocale, dir: 'ltr' | 'rtl') => {
  if (typeof document !== 'undefined') {
    document.documentElement.lang = locale
    document.documentElement.dir = dir
    if (dir === 'rtl') {
      document.documentElement.classList.add('rtl-layout')
    } else {
      document.documentElement.classList.remove('rtl-layout')
    }
  }
}

const initialLocale = getInitialLocale()
const initialDir = initialLocale === 'fa' ? 'rtl' : 'ltr'
applyHtmlAttributes(initialLocale, initialDir)

export const useLocaleStore = create<LocaleState>((set, get) => ({
  locale: initialLocale,
  dir: initialDir,

  setLocale: (locale: SupportedLocale) => {
    const meta = SUPPORTED_LOCALES.find((l) => l.code === locale)
    const dir = meta ? meta.dir : 'ltr'
    try {
      localStorage.setItem('aether_locale', locale)
    } catch {}
    applyHtmlAttributes(locale, dir)
    set({ locale, dir })
  },

  t: (key: string, defaultText?: string) => {
    const { locale } = get()
    const dict = translations[locale] || translations.en
    return dict[key] || translations.en[key] || defaultText || key
  },
}))
