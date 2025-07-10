import { createI18n } from 'vue-i18n'
import { messages } from '../locales'

// Get initial locale from localStorage, default to zh
const initialLocale = localStorage.getItem('language') || 'zh'

// Verify messages are properly loaded
if (!messages || !messages.zh || !messages.en) {
  console.error('❌ i18n messages not loaded properly:', { messages })
} else {
  console.log('✅ i18n messages loaded:', Object.keys(messages))
}

// Create i18n instance with default locale
export const i18n = createI18n({
  legacy: false,
  locale: initialLocale,
  fallbackLocale: 'zh',
  messages,
  silentTranslationWarn: false,
  silentFallbackWarn: false,
  missingWarn: true,
  fallbackWarn: true
})

// Set language and ensure it's stored in both localStorage and applies immediately
export function setLanguage(lang) {
  console.log(`Language changing from ${i18n.global.locale.value} to ${lang}`)
  
  // Update i18n locale immediately
  i18n.global.locale.value = lang
  
  // Store in localStorage for persistence
  localStorage.setItem('language', lang)
  
  // Apply language change to document for any CSS-based changes
  document.documentElement.setAttribute('lang', lang)
  
  console.log(`✅ Language changed to: ${lang}`)
}

export function getLanguage() {
  return i18n.global.locale.value
}
