import { reactive } from 'vue'

const THEME_KEY = 'lexy_lab_theme'
const mediaQuery = window.matchMedia?.('(prefers-color-scheme: dark)')

export const themeState = reactive({
  preference: localStorage.getItem(THEME_KEY) || 'system',
  resolved: 'light',
})

function systemTheme() {
  return mediaQuery?.matches ? 'dark' : 'light'
}

export function applyTheme() {
  themeState.resolved = themeState.preference === 'system' ? systemTheme() : themeState.preference
  document.documentElement.dataset.theme = themeState.resolved
  document.documentElement.dataset.themePreference = themeState.preference
  document.documentElement.style.colorScheme = themeState.resolved
}

export function setTheme(preference) {
  themeState.preference = preference
  if (preference === 'system') localStorage.removeItem(THEME_KEY)
  else localStorage.setItem(THEME_KEY, preference)
  applyTheme()
}

export function cycleTheme() {
  const order = ['system', 'light', 'dark']
  const index = order.indexOf(themeState.preference)
  setTheme(order[(index + 1) % order.length])
}

export function initTheme() {
  applyTheme()
  mediaQuery?.addEventListener?.('change', () => {
    if (themeState.preference === 'system') applyTheme()
  })
}
