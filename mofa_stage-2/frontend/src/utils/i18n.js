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

// Create i18n instance with default locale - Vue I18n v9 configuration
export const i18n = createI18n({
  legacy: false, // Use Composition API
  locale: initialLocale,
  fallbackLocale: 'zh',
  messages,
  globalInjection: true, // Enable global $t function
  silentTranslationWarn: false,
  silentFallbackWarn: false
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
  console.log('🧪 Test translation:', i18n.global.t('settings.save'))
}

export function getLanguage() {
  return i18n.global.locale.value
}
