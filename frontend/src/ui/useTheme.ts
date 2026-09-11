import { useCallback, useEffect, useState } from 'react'

type Mode = 'light' | 'dark' | 'system'

const KEY = 'vss-theme'

function read(): Mode {
  try {
    const saved = localStorage.getItem(KEY)
    if (saved === 'light' || saved === 'dark') return saved
  } catch { /* приватный режим — просто идём от системы */ }
  return 'system'
}

/** Тема: выбор пользователя перекрывает системный, иначе следуем за системой. */
export function useTheme() {
  const [mode, setMode] = useState<Mode>(read)
  const [resolved, setResolved] = useState<'light' | 'dark'>(() =>
    read() === 'system'
      ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
      : (read() as 'light' | 'dark'),
  )

  useEffect(() => {
    const root = document.documentElement
    if (mode === 'system') {
      delete root.dataset.theme
      try { localStorage.removeItem(KEY) } catch { /* игнорируем */ }
    } else {
      root.dataset.theme = mode
      try { localStorage.setItem(KEY, mode) } catch { /* игнорируем */ }
    }

    const media = window.matchMedia('(prefers-color-scheme: dark)')
    const apply = () => setResolved(mode === 'system' ? (media.matches ? 'dark' : 'light') : mode)
    apply()
    media.addEventListener('change', apply)
    return () => media.removeEventListener('change', apply)
  }, [mode])

  const toggle = useCallback(() => {
    setMode((current) => {
      const now = current === 'system'
        ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
        : current
      return now === 'dark' ? 'light' : 'dark'
    })
  }, [])

  return { mode, resolved, toggle }
}
