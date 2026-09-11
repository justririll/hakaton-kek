/**
 * Цветовые роли витрины.
 *
 * Значения живут в CSS-переменных (см. styles/theme.css) и переключаются вместе
 * с темой, поэтому код оперирует ссылками `var(--…)`, а не конкретными hex.
 *
 * Палитра кластеров прошла машинную проверку в обоих режимах на полном наборе
 * пар (диаграмма рассеяния сравнивает все пары сразу). Разделимость под
 * протанопией/дейтеранопией попадает в полосу 6–8 ΔE — это допустимо только со
 * вторым каналом кодирования, поэтому кластер всюду несёт ещё и форму маркера
 * (CLUSTER_MARKS) и прямую подпись.
 */

export const clusterColor = (id: number) => `var(--c-${((id % 5) + 5) % 5})`
export const clusterWash = (id: number, amount = 12) =>
  `color-mix(in oklab, ${clusterColor(id)} ${amount}%, transparent)`

export const channelColor = (index: number) => `var(--ch-${((index % 4) + 4) % 4})`

/** Второй канал кодирования кластера — форма маркера. */
export const CLUSTER_MARKS = ['circle', 'square', 'triangle', 'diamond', 'cross'] as const
export type MarkShape = (typeof CLUSTER_MARKS)[number]
export const clusterMark = (id: number): MarkShape => CLUSTER_MARKS[((id % 5) + 5) % 5]

export const STATUS_META: Record<
  string,
  { label: string; color: string; tone: 'good' | 'warn' | 'serious' | 'crit' | 'none'; hint: string }
> = {
  опережение: {
    label: 'Опережение',
    color: 'var(--st-good)',
    tone: 'good',
    hint: 'Текущий темп выводит на цифру выше годовой цели',
  },
  'в графике': {
    label: 'В графике',
    color: 'var(--st-good)',
    tone: 'good',
    hint: 'Текущий темп выводит на годовую цель',
  },
  риск: {
    label: 'Риск',
    color: 'var(--st-warn)',
    tone: 'warn',
    hint: 'При сохранении темпа цель года не закрывается',
  },
  срыв: {
    label: 'Срыв',
    color: 'var(--st-crit)',
    tone: 'crit',
    hint: 'Разрыв с целью слишком велик для оставшегося срока',
  },
  'без базы': {
    label: 'Без базы',
    color: 'var(--st-none)',
    tone: 'none',
    hint: 'База 2025 года не заполнена — сравнивать не с чем',
  },
}

export const SEVERITY_META: Record<string, { label: string; color: string }> = {
  error: { label: 'ошибка', color: 'var(--st-crit)' },
  warning: { label: 'предупреждение', color: 'var(--st-warn)' },
  info: { label: 'пометка', color: 'var(--st-none)' },
}

export const REC_META: Record<string, { label: string; short: string }> = {
  fix_format: { label: 'Поднять наполняемость существующего формата', short: 'Наполняемость' },
  expand_format: { label: 'Нарастить работающий формат', short: 'Расширение' },
  launch_format: { label: 'Запустить отсутствующий формат', short: 'Запуск формата' },
  raise_conversion: { label: 'Поднять выход творческих продуктов', short: 'Конверсия' },
  monetize: { label: 'Ввести платный сегмент', short: 'Монетизация' },
  amplify_visibility: { label: 'Усилить медийное сопровождение', short: 'Медиа' },
  plan_risk: { label: 'Закрыть риск по годовому плану', short: 'План года' },
}

/** Последовательная шкала (один тон) для тепловых карт. */
export const SEQ = ['var(--seq-1)', 'var(--seq-2)', 'var(--seq-3)', 'var(--seq-4)', 'var(--seq-5)', 'var(--seq-6)']

/** Расходящаяся шкала: тёплый ↔ холодный полюс, серая середина = «ничего». */
export const diverging = (t: number): string => {
  // t ∈ [-1, 1]
  const clamped = Math.max(-1, Math.min(1, t))
  if (Math.abs(clamped) < 0.04) return 'var(--rule-2)'
  const weight = Math.round(Math.min(100, 18 + Math.abs(clamped) * 72))
  const pole = clamped > 0 ? 'var(--c-0)' : 'var(--c-2)'
  return `color-mix(in oklab, ${pole} ${weight}%, var(--panel))`
}
