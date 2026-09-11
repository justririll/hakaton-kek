/** Форматирование чисел и дат по-русски: одно место на всю витрину. */

const nf = (options: Intl.NumberFormatOptions) => new Intl.NumberFormat('ru-RU', options)

const int = nf({ maximumFractionDigits: 0 })
const one = nf({ maximumFractionDigits: 1, minimumFractionDigits: 1 })
const two = nf({ maximumFractionDigits: 2 })

export const DASH = '—'

/** Целое с неразрывными разрядами. */
export function num(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return DASH
  return int.format(value)
}

const fixed = new Map<number, Intl.NumberFormat>()
export function dec(value: number | null | undefined, digits = 1): string {
  if (value == null || !Number.isFinite(value)) return DASH
  if (digits === 1) return one.format(value)
  let formatter = fixed.get(digits)
  if (!formatter) {
    formatter = nf({ maximumFractionDigits: digits, minimumFractionDigits: digits })
    fixed.set(digits, formatter)
  }
  return formatter.format(value)
}

/** Компактная запись для крупных значений: 4 193 · 12,9 тыс. · 25,0 млн. */
export function compact(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return DASH
  const abs = Math.abs(value)
  if (abs >= 1e9) return `${one.format(value / 1e9)} млрд`
  if (abs >= 1e6) return `${one.format(value / 1e6)} млн`
  if (abs >= 1e4) return `${one.format(value / 1e3)} тыс.`
  return int.format(Math.round(value))
}

/** Рубли: на витрине почти всегда нужны миллионы, а не восемь разрядов. */
export function money(value: number | null | undefined, compactForm = true): string {
  if (value == null || !Number.isFinite(value)) return DASH
  if (!compactForm) return `${int.format(Math.round(value))} ₽`
  return `${compact(value)} ₽`
}

export function pct(value: number | null | undefined, digits = 0): string {
  if (value == null || !Number.isFinite(value)) return DASH
  return `${nf({ maximumFractionDigits: digits, minimumFractionDigits: digits }).format(value * 100)}%`
}

/** Прирост со знаком: направление читается без цвета. */
export function delta(value: number | null | undefined, digits = 1): string {
  if (value == null || !Number.isFinite(value)) return DASH
  const sign = value > 0 ? '+' : value < 0 ? '−' : '±'
  return `${sign}${nf({ maximumFractionDigits: digits, minimumFractionDigits: digits }).format(Math.abs(value * 100))}%`
}

export function signed(value: number | null | undefined, digits = 2): string {
  if (value == null || !Number.isFinite(value)) return DASH
  const sign = value > 0 ? '+' : value < 0 ? '−' : '±'
  return `${sign}${two.format(Math.abs(value)).replace(/^/, '')}`.replace('+-', '−') +
    (digits === 0 ? '' : '')
}

/** Значение с единицей измерения: ₽ приклеивается, остальное — через пробел. */
export function withUnit(value: number | null | undefined, unit: string | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return DASH
  if (unit === '₽') return money(value)
  return `${compact(value)}${unit ? ` ${unit}` : ''}`
}

export function plural(n: number, forms: [string, string, string]): string {
  const abs = Math.abs(n) % 100
  const last = abs % 10
  if (abs > 10 && abs < 20) return forms[2]
  if (last > 1 && last < 5) return forms[1]
  if (last === 1) return forms[0]
  return forms[2]
}
