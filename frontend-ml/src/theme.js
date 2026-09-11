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
  опережение: { color: STATUS.good, label: 'Опережение' },
  'в графике': { color: STATUS.good, label: 'В графике' },
  риск: { color: STATUS.warning, label: 'Риск' },
  срыв: { color: STATUS.critical, label: 'Срыв' },
  'без базы': { color: '#898781', label: 'Без базы' },
}

export const SEVERITY = {
  error: { color: STATUS.critical, label: 'ошибка' },
  warning: { color: STATUS.warning, label: 'предупреждение' },
  info: { color: '#898781', label: 'наблюдение' },
}

export const CLUSTER_METAS = {
  0: {
    id: 0,
    index: '01',
    code: 'MASS',
    name: 'Массовые просветители',
    shortName: 'Просветители',
    color: '#3b82f6',
    glow: 'rgba(59, 130, 246, 0.12)',
    motto: 'Широкий охват и открытые лекции',
    badge: 'Массовый охват',
    description: 'Центры с большим потоком участников на общедоступных вводных курсах и открытых встречах.',
  },
  1: {
    id: 1,
    index: '02',
    code: 'MEDIA',
    name: 'Медийные площадки',
    shortName: 'Медиа-хабы',
    color: '#ec4899',
    glow: 'rgba(236, 72, 153, 0.12)',
    motto: 'Федеральный PR и выставочные площадки',
    badge: 'Медиа & PR',
    description: 'Лидеры по числу публикаций в СМИ и представленности на федеральных культурных событиях.',
  },
  2: {
    id: 2,
    index: '03',
    code: 'PROD',
    name: 'Продуктовые мастерские',
    shortName: 'Мастерские',
    color: '#10b981',
    glow: 'rgba(16, 185, 129, 0.12)',
    motto: 'Высокая конверсия в готовые арт-продукты',
    badge: 'Арт-результат',
    description: 'Инкубаторы полного цикла: почти каждый участник создает реальную работу или прототип.',
  },
  3: {
    id: 3,
    index: '04',
    code: 'OPEN',
    name: 'Открытые бесплатные площадки',
    shortName: 'Городские хабы',
    color: '#f59e0b',
    glow: 'rgba(245, 158, 11, 0.12)',
    motto: 'Социальная миссия и городские сообщества',
    badge: 'Социальные хабы',
    description: 'Пространства с нулевым барьером входа и бесплатными сервисами для творческих команд.',
  },
  4: {
    id: 4,
    index: '05',
    code: 'ACAD',
    name: 'Профессиональные академии',
    shortName: 'Академии',
    color: '#8b5cf6',
    glow: 'rgba(139, 92, 246, 0.12)',
    motto: 'Глубокие программы ДПО и монетизация',
    badge: 'Проф. ДПО',
    description: 'Длительные программы повышения квалификации, переподготовка и стабильная платная модель.',
  },
}

export function getClusterMeta(idOrName) {
  if (typeof idOrName === 'number') {
    return CLUSTER_METAS[idOrName] || { name: `Кластер ${idOrName}`, color: '#3b82f6', index: '00', code: 'CLS' }
  }
  const byName = Object.values(CLUSTER_METAS).find((c) => c.name === idOrName)
  return byName || { name: String(idOrName), color: '#3b82f6', index: '00', code: 'CLS' }
}

export function percent(value, decimals = 0) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return `${(value * 100).toFixed(decimals).replace('.', ',')}%`
}

export function isDark() {
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

export function money(value) {
  if (value === null || value === undefined) return '—'
  if (Math.abs(value) >= 1e6) return `${(value / 1e6).toFixed(1).replace('.', ',')} млн ₽`
  return `${new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 }).format(value)} ₽`
}
