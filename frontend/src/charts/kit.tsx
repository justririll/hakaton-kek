/**
 * Каркас графиков: измерение контейнера, оси-волосяные линии, подсказка,
 * маркеры кластеров.
 *
 * Все графики рисуются вручную в SVG. Готовая библиотека тянет за собой свой
 * визуальный язык — рамки, тени, скруглённые толстые столбцы, — который пришлось
 * бы переопределять по частям. Здесь спецификация штриха одна на всю витрину:
 * столбец ≤ 24 px со скруглённым концом, линия 2 px, маркер ≥ 8 px с кольцом
 * цвета подложки, сетка — сплошная волосяная линия на один шаг от фона.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import type { MarkShape } from '../lib/palette'

/* ── размеры ──────────────────────────────────────────────────────────────── */

export function useMeasure<T extends HTMLElement>() {
  const ref = useRef<T>(null)
  const [size, setSize] = useState({ width: 0, height: 0 })

  useEffect(() => {
    const node = ref.current
    if (!node) return
    const observer = new ResizeObserver(([entry]) => {
      const box = entry.contentRect
      setSize({ width: Math.round(box.width), height: Math.round(box.height) })
    })
    observer.observe(node)
    return () => observer.disconnect()
  }, [])

  return { ref, ...size }
}

export interface Margin { top: number; right: number; bottom: number; left: number }

/* ── оси ──────────────────────────────────────────────────────────────────── */

export function GridY({
  ticks, x0, x1, scale,
}: { ticks: number[]; x0: number; x1: number; scale: (v: number) => number }) {
  return (
    <g aria-hidden>
      {ticks.map((tick) => (
        <line
          key={tick}
          x1={x0}
          x2={x1}
          y1={scale(tick)}
          y2={scale(tick)}
          stroke="var(--rule)"
          strokeWidth={1}
          shapeRendering="crispEdges"
        />
      ))}
    </g>
  )
}

export function AxisLeft({
  ticks, scale, x, format,
}: { ticks: number[]; scale: (v: number) => number; x: number; format: (v: number) => string }) {
  return (
    <g aria-hidden>
      {ticks.map((tick) => (
        <text
          key={tick}
          x={x - 8}
          y={scale(tick)}
          textAnchor="end"
          dominantBaseline="central"
          className="tnum fill-ink-3 text-[10.5px]"
        >
          {format(tick)}
        </text>
      ))}
    </g>
  )
}

export function AxisBottom({
  ticks, scale, y, format, anchor = 'middle',
}: {
  ticks: number[]
  scale: (v: number) => number
  y: number
  format: (v: number) => string
  anchor?: 'middle' | 'start' | 'end'
}) {
  return (
    <g aria-hidden>
      {ticks.map((tick) => (
        <text
          key={tick}
          x={scale(tick)}
          y={y + 14}
          textAnchor={anchor}
          className="tnum fill-ink-3 text-[10.5px]"
        >
          {format(tick)}
        </text>
      ))}
    </g>
  )
}

export function Baseline({ x0, x1, y }: { x0: number; x1: number; y: number }) {
  return <line x1={x0} x2={x1} y1={y} y2={y} stroke="var(--rule-2)" strokeWidth={1} shapeRendering="crispEdges" />
}

/* ── маркеры кластеров (второй канал кодирования) ─────────────────────────── */

export function ClusterMark({
  shape, x, y, r, fill, ring = 'var(--panel)', opacity = 1, strokeWidth = 2,
}: {
  shape: MarkShape
  x: number
  y: number
  r: number
  fill: string
  ring?: string
  opacity?: number
  strokeWidth?: number
}) {
  const common = { fill, stroke: ring, strokeWidth, opacity, strokeLinejoin: 'round' as const }
  switch (shape) {
    case 'square':
      return <rect x={x - r * 0.88} y={y - r * 0.88} width={r * 1.76} height={r * 1.76} rx={1.5} {...common} />
    case 'triangle':
      return (
        <path
          d={`M${x} ${y - r * 1.12}L${x + r * 1.02} ${y + r * 0.72}L${x - r * 1.02} ${y + r * 0.72}Z`}
          {...common}
        />
      )
    case 'diamond':
      return <path d={`M${x} ${y - r * 1.2}L${x + r * 1.2} ${y}L${x} ${y + r * 1.2}L${x - r * 1.2} ${y}Z`} {...common} />
    case 'cross':
      return (
        <path
          d={`M${x - r * 1.25} ${y - r * 0.42}h${r * 0.83}v-${r * 0.83}h${r * 0.84}v${r * 0.83}h${r * 0.83}v${r * 0.84}h-${r * 0.83}v${r * 0.83}h-${r * 0.84}v-${r * 0.83}h-${r * 0.83}Z`}
          {...common}
        />
      )
    default:
      return <circle cx={x} cy={y} r={r} {...common} />
  }
}

/* ── подсказка ────────────────────────────────────────────────────────────── */

export interface TipState { x: number; y: number; content: ReactNode }

export function useTooltip() {
  const [tip, setTip] = useState<TipState | null>(null)
  const show = useCallback((x: number, y: number, content: ReactNode) => setTip({ x, y, content }), [])
  const hide = useCallback(() => setTip(null), [])
  return { tip, show, hide }
}

export function Tooltip({ tip, width }: { tip: TipState | null; width: number }) {
  if (!tip) return null
  // Подсказка у правого края переворачивается, иначе её обрезает панель.
  const flip = tip.x > width - 190
  return (
    <div
      className="pointer-events-none absolute z-30 max-w-[280px] min-w-[140px] rounded-sm border border-rule-2 bg-panel px-2.5 py-2 text-[11.5px] leading-snug shadow-pop"
      style={{
        left: flip ? undefined : tip.x + 14,
        right: flip ? width - tip.x + 14 : undefined,
        top: Math.max(4, tip.y - 12),
      }}
    >
      {tip.content}
    </div>
  )
}

export function TipRow({ label, value, strong }: { label: string; value: ReactNode; strong?: boolean }) {
  return (
    <div className="flex items-baseline justify-between gap-4">
      <span className="text-ink-3">{label}</span>
      <span className={`tnum ${strong ? 'font-semibold text-ink' : 'text-ink-2'}`}>{value}</span>
    </div>
  )
}

export function TipTitle({ children, color, mark }: { children: ReactNode; color?: string; mark?: ReactNode }) {
  return (
    <div className="mb-1.5 flex items-center gap-1.5 border-b border-rule pb-1.5 font-semibold text-ink">
      {mark ?? (color && <span className="size-2 shrink-0 rounded-full" style={{ background: color }} />)}
      <span className="truncate">{children}</span>
    </div>
  )
}

/* ── легенда ──────────────────────────────────────────────────────────────── */

export function Legend({
  items, onHover, active, className = '',
}: {
  items: Array<{ label: string; color: string; shape?: MarkShape; id?: string | number }>
  onHover?: (id: string | number | null) => void
  active?: string | number | null
  className?: string
}) {
  return (
    <ul className={`flex flex-wrap items-center gap-x-4 gap-y-1.5 ${className}`}>
      {items.map((item, index) => {
        const dim = active != null && item.id != null && active !== item.id
        return (
          <li
            key={item.id ?? index}
            onMouseEnter={() => onHover?.(item.id ?? null)}
            onMouseLeave={() => onHover?.(null)}
            className={`flex items-center gap-1.5 text-[11.5px] transition-opacity duration-150 ${
              dim ? 'opacity-40' : ''
            } ${onHover ? 'cursor-default' : ''}`}
          >
            {item.shape ? (
              <svg width={11} height={11} viewBox="-6 -6 12 12" aria-hidden className="shrink-0">
                <ClusterMark shape={item.shape} x={0} y={0} r={4.2} fill={item.color} strokeWidth={0} />
              </svg>
            ) : (
              <span aria-hidden className="size-2.5 shrink-0 rounded-[2px]" style={{ background: item.color }} />
            )}
            <span className="text-ink-2">{item.label}</span>
          </li>
        )
      })}
    </ul>
  )
}

/* ── контейнер ────────────────────────────────────────────────────────────── */

/**
 * Высота задаётся контейнеру целиком вместе с полосой подписей оси — иначе
 * внутри карточки появляется собственная полоса прокрутки на 12 пикселей.
 */
export function ChartBox({
  height, children, className = '',
}: { height: number; children: (size: { width: number; height: number }) => ReactNode; className?: string }) {
  const { ref, width } = useMeasure<HTMLDivElement>()
  return (
    <div ref={ref} className={`relative w-full ${className}`} style={{ height }}>
      {width > 0 && children({ width, height })}
    </div>
  )
}
