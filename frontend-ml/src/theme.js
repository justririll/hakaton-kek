/**
 * Палитра и общая настройка графиков.
 *
 * Значения цветов взяты из проверенного справочного набора и подобраны так,
 * чтобы проходить контроль цветовой различимости в обеих темах. Важное
 * ограничение: набор из пяти категориальных цветов не проходит проверку по
 * всем парам сразу (а на диаграмме рассеяния в сравнении участвуют именно все
 * пары). Поэтому кластеры на точечной диаграмме показываются малыми кратными —
 * один кластер выделен, остальные приглушены, — а пять цветов используются
 * только там, где сравниваются соседние элементы.
 */

const LIGHT = {
  surface: '#fcfcfb',
  plane: '#f9f9f7',
  textPrimary: '#0b0b0b',
  textSecondary: '#52514e',
  muted: '#898781',
  grid: '#e1e0d9',
  axis: '#c3c2b7',
  border: 'rgba(11,11,11,0.10)',
  // Смежные пары: используется для составных столбиков (4 канала аудитории).
  series: ['#2a78d6', '#eb6834', '#1baf7a', '#eda100'],
  accent: '#2a78d6',
  dim: '#c9c8c1',
}

const DARK = {
  surface: '#1a1a19',
  plane: '#0d0d0d',
  textPrimary: '#ffffff',
  textSecondary: '#c3c2b7',
  muted: '#898781',
  grid: '#2c2c2a',
  axis: '#383835',
  border: 'rgba(255,255,255,0.10)',
  series: ['#3987e5', '#d95926', '#199e70', '#c98500'],
  accent: '#3987e5',
  dim: '#4a4a46',
}

// Статусные цвета фиксированы и не участвуют в категориальной палитре:
// статус всегда сопровождается подписью, цвет его не несёт в одиночку.
export const STATUS = {
  good: '#0ca30c',
  warning: '#fab219',
  serious: '#ec835a',
  critical: '#d03b3b',
}

export const PLAN_STATUS = {
  опережение: { color: STATUS.good, icon: '▲' },
  'в графике': { color: STATUS.good, icon: '●' },
  риск: { color: STATUS.warning, icon: '▲' },
  срыв: { color: STATUS.critical, icon: '■' },
  'без базы': { color: '#898781', icon: '—' },
}

export const SEVERITY = {
  error: { color: STATUS.critical, icon: '■', label: 'ошибка' },
  warning: { color: STATUS.warning, icon: '▲', label: 'предупреждение' },
  info: { color: '#898781', icon: '●', label: 'наблюдение' },
}

export function isDark() {
  // Функция вызывается при сборке опций графика, в том числе вне браузера
  // (серверный рендер, тесты). Без DOM считаем тему светлой, а не падаем.
  if (typeof document === 'undefined' || typeof window === 'undefined') return false
  const stamped = document.documentElement.dataset.theme
  if (stamped === 'dark') return true
  if (stamped === 'light') return false
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

export function palette() {
  return isDark() ? DARK : LIGHT
}

/** Общие настройки графика: тонкие метки, сплошная сетка-волосок, без рамок. */
export function baseOption() {
  const p = palette()
  return {
    backgroundColor: 'transparent',
    textStyle: {
      fontFamily: 'system-ui, -apple-system, "Segoe UI", sans-serif',
      color: p.textSecondary,
    },
    grid: { left: 8, right: 16, top: 24, bottom: 8, containLabel: true },
    tooltip: {
      backgroundColor: p.surface,
      borderColor: p.border,
      borderWidth: 1,
      textStyle: { color: p.textPrimary, fontSize: 12 },
      extraCssText: 'box-shadow: 0 4px 16px rgba(0,0,0,0.12); border-radius: 8px;',
    },
  }
}

export function axisStyle() {
  const p = palette()
  return {
    axisLine: { show: true, lineStyle: { color: p.axis, width: 1 } },
    axisTick: { show: false },
    splitLine: { show: true, lineStyle: { color: p.grid, width: 1, type: 'solid' } },
    axisLabel: { color: p.muted, fontSize: 11 },
  }
}

/** Компактная запись больших чисел: 1 284 → «1 284», 12 900 → «12,9 тыс.». */
export function compact(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  const abs = Math.abs(value)
  if (abs >= 1e6) return `${(value / 1e6).toFixed(1).replace('.', ',')} млн`
  if (abs >= 1e4) return `${(value / 1e3).toFixed(1).replace('.', ',')} тыс.`
  return new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 2 }).format(value)
}

/** Склоняет существительное по числу: 1 центр, 2 центра, 5 центров. */
export function plural(count, one, few, many) {
  const mod100 = Math.abs(count) % 100
  const mod10 = mod100 % 10
  if (mod100 >= 11 && mod100 <= 14) return `${count} ${many}`
  if (mod10 === 1) return `${count} ${one}`
  if (mod10 >= 2 && mod10 <= 4) return `${count} ${few}`
  return `${count} ${many}`
}

/** Счётная величина: людей и работ не бывает 1 689,9. */
export function count(value) {
  return compact(Math.round(value ?? 0))
}

export function money(value) {
  if (value === null || value === undefined) return '—'
  if (Math.abs(value) >= 1e6) return `${(value / 1e6).toFixed(1).replace('.', ',')} млн ₽`
  return `${new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 }).format(value)} ₽`
}
