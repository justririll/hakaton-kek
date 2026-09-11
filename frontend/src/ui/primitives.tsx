/** Базовые элементы витрины: панель, метки, переключатели, подсказки. */

import { useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { Icon } from './Icon'
import type { IconName } from './Icon'

/* ── панель ───────────────────────────────────────────────────────────────── */

interface PanelProps {
  eyebrow?: string
  title?: ReactNode
  subtitle?: ReactNode
  actions?: ReactNode
  footnote?: ReactNode
  children: ReactNode
  className?: string
  bodyClassName?: string
}

export function Panel({
  eyebrow, title, subtitle, actions, footnote, children, className = '', bodyClassName = '',
}: PanelProps) {
  return (
    <section
      className={`panel flex min-w-0 flex-col overflow-hidden shadow-card ${className}`}
    >
      {(title || eyebrow || actions) && (
        // Заголовок и элементы управления переносятся, а не сжимают друг друга:
        // при длинном переключателе заголовок иначе схлопывается в узкую колонку.
        <header className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2.5 px-4 pt-3.5 pb-3">
          <div className="min-w-[min(100%,260px)] flex-1">
            {eyebrow && <div className="eyebrow mb-1.5">{eyebrow}</div>}
            {title && <h3 className="text-[15px] leading-tight font-medium text-ink">{title}</h3>}
            {subtitle && <p className="mt-1 max-w-prose text-[12.5px] leading-snug text-ink-2">{subtitle}</p>}
          </div>
          {actions && <div className="flex shrink-0 items-center gap-1.5">{actions}</div>}
        </header>
      )}
      <div className={`min-w-0 flex-1 px-4 pb-4 ${bodyClassName}`}>{children}</div>
      {footnote && (
        <footer className="rule-t bg-panel-2 px-4 py-2.5 text-[11.5px] leading-snug text-ink-3">
          {footnote}
        </footer>
      )}
    </section>
  )
}

/* ── метки ────────────────────────────────────────────────────────────────── */

export function Chip({
  children, color, tone = 'plain', mark, className = '',
}: {
  children: ReactNode
  color?: string
  tone?: 'plain' | 'solid' | 'outline'
  mark?: boolean
  className?: string
}) {
  const base =
    'inline-flex items-center gap-1.5 rounded-xs px-1.5 py-[3px] text-[11px] leading-none font-medium whitespace-nowrap'
  if (tone === 'solid') {
    return (
      <span
        className={`${base} text-ink-inv ${className}`}
        style={{ background: color ?? 'var(--ink)' }}
      >
        {children}
      </span>
    )
  }
  return (
    <span
      className={`${base} border text-ink-2 ${className}`}
      style={
        color
          ? { borderColor: `color-mix(in oklab, ${color} 40%, transparent)`, background: `color-mix(in oklab, ${color} 9%, transparent)` }
          : { borderColor: 'var(--rule-2)' }
      }
    >
      {mark && color && (
        <span aria-hidden className="size-[7px] shrink-0 rounded-full" style={{ background: color }} />
      )}
      {children}
    </span>
  )
}

/** Статус всегда идёт значком и подписью — цвет сам по себе ничего не сообщает. */
export function StatusTag({ label, color, icon }: { label: string; color: string; icon: IconName }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-[12px] whitespace-nowrap text-ink-2">
      <span style={{ color }} className="flex shrink-0">
        <Icon name={icon} size={13} strokeWidth={2} />
      </span>
      {label}
    </span>
  )
}

/* ── переключатель ────────────────────────────────────────────────────────── */

export function Segmented<T extends string>({
  value, options, onChange, size = 'md', ariaLabel,
}: {
  value: T
  options: Array<{ value: T; label: string; hint?: string }>
  onChange: (value: T) => void
  size?: 'sm' | 'md'
  ariaLabel: string
}) {
  const pad = size === 'sm' ? 'px-2 py-[3px] text-[11.5px]' : 'px-2.5 py-[5px] text-[12.5px]'
  return (
    // На узком экране лента прокручивается вбок: перенос разорвал бы группу,
    // а сжатие сделало бы подписи нечитаемыми.
    <div
      role="tablist"
      aria-label={ariaLabel}
      className="flex max-w-full items-center gap-0.5 overflow-x-auto rounded-sm border border-rule bg-panel-2 p-0.5"
    >
      {options.map((option) => {
        const active = option.value === value
        return (
          <button
            key={option.value}
            role="tab"
            aria-selected={active}
            title={option.hint}
            onClick={() => onChange(option.value)}
            className={`${pad} rounded-xs font-medium whitespace-nowrap transition-colors duration-150 ${
              active
                ? 'bg-ink text-ink-inv'
                : 'text-ink-2 hover:bg-panel-3 hover:text-ink'
            }`}
          >
            {option.label}
          </button>
        )
      })}
    </div>
  )
}

/* ── кнопки ───────────────────────────────────────────────────────────────── */

export function Button({
  children, onClick, variant = 'ghost', icon, disabled, title, className = '',
}: {
  children?: ReactNode
  onClick?: () => void
  variant?: 'ghost' | 'solid' | 'outline'
  icon?: IconName
  disabled?: boolean
  title?: string
  className?: string
}) {
  const styles = {
    ghost: 'text-ink-2 hover:bg-panel-3 hover:text-ink',
    solid: 'bg-ink text-ink-inv hover:opacity-88',
    outline: 'border border-rule-2 text-ink-2 hover:border-rule-strong hover:text-ink',
  }[variant]
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={`inline-flex min-h-[28px] items-center gap-1.5 rounded-sm px-2.5 text-[12.5px] font-medium transition-all duration-150 disabled:cursor-not-allowed disabled:opacity-45 ${styles} ${className}`}
    >
      {icon && <Icon name={icon} size={14} />}
      {children}
    </button>
  )
}

/* ── подсказка при наведении ──────────────────────────────────────────────── */

export function Hint({ text, children }: { text: string; children: ReactNode }) {
  const [open, setOpen] = useState(false)
  return (
    <span
      className="relative inline-flex"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
      tabIndex={0}
    >
      {children}
      {open && (
        <span
          role="tooltip"
          className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-1.5 w-max max-w-[260px] -translate-x-1/2 rounded-sm border border-rule-2 bg-panel px-2 py-1.5 text-[11.5px] leading-snug font-normal text-ink-2 shadow-pop"
        >
          {text}
        </span>
      )}
    </span>
  )
}

export function InfoDot({ text }: { text: string }) {
  return (
    <Hint text={text}>
      <span className="inline-flex size-4 cursor-help items-center justify-center rounded-full border border-rule-2 text-ink-3 transition-colors hover:border-rule-strong hover:text-ink-2">
        <Icon name="info" size={11} strokeWidth={1.8} />
      </span>
    </Hint>
  )
}

/* ── модальное окно ───────────────────────────────────────────────────────── */

export function Sheet({
  open, onClose, children, label,
}: {
  open: boolean
  onClose: () => void
  children: ReactNode
  label: string
}) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const onKey = (event: KeyboardEvent) => { if (event.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    const previous = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    ref.current?.focus()
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = previous
    }
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-100 flex justify-end" role="dialog" aria-modal="true" aria-label={label}>
      <button
        aria-label="Закрыть"
        onClick={onClose}
        className="absolute inset-0 cursor-default bg-[color-mix(in_oklab,var(--ink)_38%,transparent)] backdrop-blur-[1px]"
        style={{ animation: 'vss-fade 180ms ease-out' }}
      />
      <div
        ref={ref}
        tabIndex={-1}
        className="relative flex h-full w-full max-w-[min(920px,94vw)] flex-col border-l border-rule bg-paper shadow-pop outline-none"
        style={{ animation: 'vss-slide 260ms cubic-bezier(0.22, 1, 0.36, 1)' }}
      >
        {children}
      </div>
    </div>
  )
}

/* ── заглушка загрузки ────────────────────────────────────────────────────── */

export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`animate-pulse rounded-sm bg-panel-3 ${className}`} />
}

/** Пустое состояние: честно сообщает, что данных нет, вместо нуля на графике. */
export function Empty({ text, className = '' }: { text: string; className?: string }) {
  return (
    <div className={`flex min-h-24 items-center justify-center rounded-sm border border-dashed border-rule-2 px-4 py-6 text-center text-[12.5px] text-ink-3 ${className}`}>
      {text}
    </div>
  )
}
