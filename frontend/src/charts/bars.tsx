/** Столбчатые формы: рейтинг, исполнение плана, состав аудитории. */

import { Fragment } from 'react'
import type { ReactNode } from 'react'
import { Tooltip, TipRow, TipTitle, useMeasure, useTooltip } from './kit'
import { pct } from '../lib/format'

/** Столбец со скруглённым концом и прямым основанием — конец данных виден, начало нет. */
export function barPath(x: number, y: number, width: number, height: number, radius = 4) {
  const r = Math.max(0, Math.min(radius, width, height / 2))
  if (width <= 0.5) return `M${x} ${y}h0.5v${height}h-0.5Z`
  return `M${x} ${y}h${width - r}a${r} ${r} 0 0 1 ${r} ${r}v${height - 2 * r}a${r} ${r} 0 0 1 ${-r} ${r}h${-(width - r)}Z`
}

export interface RankedItem {
  id: string
  label: string
  value: number
  color?: string
  note?: ReactNode
  tip?: ReactNode
}

/**
 * Рейтинг по горизонтали. Подписи значений стоят у конца столбца, поэтому ось
 * значений не нужна: сетка тут только мешала бы читать названия.
 */
export function RankedBars({
  items, format, maxValue, barHeight = 13, labelWidth = 132, valueWidth = 62, onSelect, highlight,
}: {
  items: RankedItem[]
  format: (value: number) => string
  maxValue?: number
  barHeight?: number
  labelWidth?: number
  valueWidth?: number
  onSelect?: (id: string) => void
  highlight?: string | null
}) {
  const max = maxValue ?? Math.max(1, ...items.map((item) => Math.abs(item.value)))
  const { tip, show, hide } = useTooltip()
  const { ref, width } = useMeasure<HTMLDivElement>()

  return (
    <div ref={ref} className="relative" onMouseLeave={hide}>
      <ul className="flex flex-col gap-[3px]">
        {items.map((item) => {
          const dim = highlight != null && highlight !== item.id
          const share = Math.max(0.008, Math.abs(item.value) / max)
          return (
            <li key={item.id}>
              <div
                role={onSelect ? 'button' : undefined}
                tabIndex={onSelect ? 0 : undefined}
                onClick={onSelect ? () => onSelect(item.id) : undefined}
                onKeyDown={onSelect ? (event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onSelect(item.id) } } : undefined}
                onMouseMove={(event) => {
                  if (!item.tip) return
                  const rect = ref.current!.getBoundingClientRect()
                  show(event.clientX - rect.left, event.clientY - rect.top, item.tip)
                }}
                className={`group flex w-full items-center gap-3 rounded-xs py-[2px] text-left transition-[opacity,background-color] duration-150 ${
                  onSelect ? 'cursor-pointer hover:bg-panel-2' : ''
                } ${dim ? 'opacity-35' : ''}`}
              >
                <span
                  className="shrink-0 truncate text-[12px] text-ink-2 group-hover:text-ink"
                  style={{ width: labelWidth }}
                  title={item.label}
                >
                  {item.label}
                </span>
                <span className="relative min-w-0 flex-1 rounded-[2px] bg-panel-2" style={{ height: barHeight }}>
                  <span
                    className="bar-grow absolute top-0 bottom-0 left-0"
                    style={{
                      width: `${share * 100}%`,
                      background: item.color ?? 'var(--ink-2)',
                      borderRadius: '2px 4px 4px 2px',
                    }}
                  />
                </span>
                <span className="tnum shrink-0 text-right text-[12px] font-medium text-ink" style={{ width: valueWidth }}>
                  {format(item.value)}
                </span>
              </div>
              {item.note && (
                <div className="pb-1 text-[11px] leading-snug text-ink-3" style={{ marginLeft: labelWidth + 12 }}>
                  {item.note}
                </div>
              )}
            </li>
          )
        })}
      </ul>
      <Tooltip tip={tip} width={width} />
    </div>
  )
}

/**
 * Исполнение годовой цели.
 *
 * Дорожка — шкала до 125 % цели, заливка — накопленный факт, вертикаль — сама
 * цель, засечка — прогноз по текущему темпу. Цвет заливки несёт статус, но
 * рядом всегда стоит доля в процентах: цвет один смысла не передаёт.
 */
export function PlanMeter({
  completion, forecastShare, color, height = 8, showGoal = true,
}: {
  completion: number
  forecastShare: number | null
  color: string
  height?: number
  showGoal?: boolean
}) {
  const span = 1.25
  const place = (value: number) => `${Math.max(0, Math.min(100, (value / span) * 100))}%`
  return (
    <div className="relative w-full" style={{ height }}>
      <div className="absolute inset-0 rounded-full bg-panel-3" />
      <div
        className="bar-grow absolute top-0 bottom-0 left-0 rounded-full"
        style={{ width: place(Math.max(0, completion)), background: color }}
      />
      {showGoal && (
        <div
          className="absolute top-[-3px] bottom-[-3px] w-px"
          style={{ left: place(1), background: 'var(--rule-strong)' }}
          title="Цель года"
        />
      )}
      {forecastShare != null && (
        <div
          className="absolute top-[-2px] bottom-[-2px] w-[2px] rounded-full"
          style={{ left: place(Math.max(0, forecastShare)), background: 'var(--ink)' }}
          title={`Прогноз по текущему темпу: ${pct(forecastShare)} цели`}
        />
      )}
    </div>
  )
}

/**
 * Состав по каналам, нормированный на 100 %.
 * Сегменты разделяет промежуток цвета подложки — обводка добавила бы лишних чернил.
 */
export function ShareBar({
  parts, height = 12, gap = 2, minLabel = 42,
}: {
  parts: Array<{ key: string; label: string; value: number; color: string }>
  height?: number
  gap?: number
  minLabel?: number
}) {
  const total = parts.reduce((sum, part) => sum + part.value, 0)
  const { tip, show, hide } = useTooltip()
  const { ref, width: box } = useMeasure<HTMLDivElement>()

  if (total <= 0) {
    return (
      <div className="hatch rounded-xs border border-rule" style={{ height }} title="Аудитория не заявлена" />
    )
  }

  let offset = 0
  const segments = parts
    .filter((part) => part.value > 0)
    .map((part) => {
      const width = (part.value / total) * 100
      const item = { ...part, left: offset, width }
      offset += width
      return item
    })

  return (
    <div ref={ref} className="relative w-full" style={{ height }} onMouseLeave={hide}>
      {segments.map((segment, index) => (
        <Fragment key={segment.key}>
          <div
            className="absolute top-0 bottom-0 rounded-[2px]"
            style={{
              left: `calc(${segment.left}% + ${index === 0 ? 0 : gap / 2}px)`,
              width: `calc(${segment.width}% - ${index === 0 || index === segments.length - 1 ? gap / 2 : gap}px)`,
              background: segment.color,
            }}
            onMouseMove={(event) => {
              const rect = event.currentTarget.parentElement!.getBoundingClientRect()
              show(
                event.clientX - rect.left,
                event.clientY - rect.top,
                <>
                  <TipTitle color={segment.color}>{segment.label}</TipTitle>
                  <TipRow label="Участников" value={segment.value.toLocaleString('ru-RU')} strong />
                  <TipRow label="Доля" value={pct(segment.value / total, 1)} />
                </>,
              )
            }}
          />
          {/* Подпись внутри сегмента — только если она туда помещается целиком. */}
          {segment.width * (box / 100) > minLabel && height >= 16 && (
            <span
              className="pointer-events-none absolute top-1/2 -translate-y-1/2 text-[10px] font-medium"
              style={{ left: `calc(${segment.left}% + 6px)`, color: 'var(--panel)' }}
            >
              {Math.round(segment.width)}%
            </span>
          )}
        </Fragment>
      ))}
      <Tooltip tip={tip} width={box} />
    </div>
  )
}
