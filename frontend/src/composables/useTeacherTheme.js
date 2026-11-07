import { ref } from 'vue'

const root = document.documentElement
const isDark = ref(root.dataset.theme === 'dark')

function toggleTheme() {
  isDark.value = !isDark.value
  root.dataset.theme = isDark.value ? 'dark' : 'light'
}

export function useTeacherTheme() {
  return { isDark, toggleTheme }
}
