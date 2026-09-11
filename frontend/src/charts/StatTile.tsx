/**
 * Плитка показателя.
 *
 * Крупное число — пропорциональными цифрами: табличные на таком кегле выглядят
 * разреженными. Направление изменения читается знаком и стрелкой, а не одним
 * лишь цветом.
 */

import type { ReactNode } from 'react'
import { Icon } from '../ui/Icon'
import { InfoDot } from '../ui/primitives'

export function StatTile({
  label, value, unit, sub, delta, deltaTone = 'neutral', hint, accent, className = '', size = 'md',
}: {
  label: string
  value: ReactNode
  unit?: string
  sub?: ReactNode
  delta?: string
  deltaTone?: 'up' | 'down' | 'neutral'
  hint?: string
  accent?: string
  className?: string
  size?: 'md' | 'lg'
}) {
  const toneColor =
    deltaTone === 'up' ? 'var(--st-good)' : deltaTone === 'down' ? 'var(--st-crit)' : 'var(--ink-3)'
  return (
    <div className={`relative flex min-w-0 flex-col justify-between gap-2 px-4 py-3.5 ${className}`}>
      {accent && (
        <span aria-hidden className="absolute top-3.5 bottom-3.5 left-0 w-[2px] rounded-full" style={{ background: accent }} />
      )}
      <div className="flex items-start gap-1.5">
        <span className="text-[11.5px] leading-snug font-medium text-ink-2">{label}</span>
        {hint && <InfoDot text={hint} />}
      </div>
      <div className="flex flex-wrap items-baseline gap-x-1.5 gap-y-0.5">
        <span className={`figure text-ink ${size === 'lg' ? 'text-[34px] leading-[1.05]' : 'text-[25px] leading-[1.1]'}`}>
          {value}
        </span>
        {unit && <span className="text-[12px] text-ink-3">{unit}</span>}
        {delta && (
          <span className="ml-1 inline-flex items-center gap-0.5 text-[11.5px] font-medium" style={{ color: toneColor }}>
            {deltaTone !== 'neutral' && <Icon name={deltaTone === 'up' ? 'arrow-up' : 'arrow-down'} size={11} strokeWidth={2.2} />}
            {delta}
          </span>
        )}
      </div>
      {sub && <div className="text-[11.5px] leading-snug text-ink-3">{sub}</div>}
    </div>
  )
}

/** Ряд плиток, разделённых волосяными линиями, как колонки в печатной таблице. */
export function StatRow({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={`panel stagger grid grid-cols-2 divide-x divide-y divide-rule overflow-hidden shadow-card md:grid-cols-3 xl:grid-cols-6 xl:divide-y-0 ${className}`}
    >
      {children}
    </div>
  )
}
