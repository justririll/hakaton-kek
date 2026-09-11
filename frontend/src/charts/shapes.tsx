/** Остальные формы: доли, распределения, траектории, дерево слияний. */

import { useMemo } from 'react'
import { scaleLinear } from 'd3-scale'
import { line as d3line, arc as d3arc, pie as d3pie } from 'd3-shape'
import { Tooltip, TipRow, TipTitle, useMeasure, useTooltip } from './kit'
import { num, pct } from '../lib/format'

/* ── доли: кольцо ─────────────────────────────────────────────────────────── */

/**
 * Кольцо уместно только для отношения части к целому и при небольшом числе
 * секторов. Сравнивать близкие значения по нему нельзя — для этого рядом стоит
 * список с числами.
 */
export function Donut({
  parts, size = 150, thickness = 18, centerLabel, centerValue,
}: {
  parts: Array<{ key: string; label: string; value: number; color: string }>
  size?: number
  thickness?: number
  centerLabel?: string
  centerValue?: string
}) {
  const { tip, show, hide } = useTooltip()
  const total = parts.reduce((sum, part) => sum + part.value, 0)
  const radius = size / 2

  const arcs = useMemo(() => {
    const layout = d3pie<{ key: string; label: string; value: number; color: string }>()
      .sort(null)
      .value((d) => d.value)
      .padAngle(0.016)
    const generator = d3arc<{ startAngle: number; endAngle: number }>()
      .innerRadius(radius - thickness)
      .outerRadius(radius)
      .cornerRadius(1.5)
    return layout(parts).map((slice) => ({ slice, d: generator(slice) ?? '' }))
  }, [parts, radius, thickness])

  return (
    <div className="relative" style={{ width: size, height: size }} onMouseLeave={hide}>
      <svg width={size} height={size} role="img" aria-label="Распределение по статусам">
        <g transform={`translate(${radius},${radius})`}>
          {arcs.map(({ slice, d }) => (
            <path
              key={slice.data.key}
              d={d}
              fill={slice.data.color}
              stroke="var(--panel)"
              strokeWidth={2}
              className="cursor-default transition-opacity duration-150 hover:opacity-80"
              onMouseMove={(event) => {
                const rect = event.currentTarget.ownerSVGElement!.parentElement!.getBoundingClientRect()
                show(
                  event.clientX - rect.left,
                  event.clientY - rect.top,
                  <>
                    <TipTitle color={slice.data.color}>{slice.data.label}</TipTitle>
                    <TipRow label="Центров" value={num(slice.data.value)} strong />
                    <TipRow label="Доля" value={pct(slice.data.value / total)} />
                  </>,
                )
              }}
            />
          ))}
        </g>
      </svg>
      {centerValue && (
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="figure text-[26px] leading-none text-ink">{centerValue}</span>
          {centerLabel && <span className="mt-1 max-w-[84px] text-center text-[10.5px] leading-tight text-ink-3">{centerLabel}</span>}
        </div>
      )}
      <Tooltip tip={tip} width={size} />
    </div>
  )
}

/* ── распределение ────────────────────────────────────────────────────────── */

/**
 * Полоса распределения: каждая организация — точка, поверх лежит межквартильный
 * размах и медиана. Двадцать наблюдений слишком мало для гистограммы, а точки
 * показывают и разброс, и выбросы, и положение выбранного центра.
 */
export function StripPlot({
  items, median, p25, p75, format, height = 64, highlight, onSelect, logScale = false,
}: {
  items: Array<{ id: string; label: string; value: number; color: string }>
  median: number
  p25: number
  p75: number
  format: (value: number) => string
  height?: number
  highlight?: string | null
  onSelect?: (id: string) => void
  logScale?: boolean
}) {
  const { ref, width } = useMeasure<HTMLDivElement>()
  const { tip, show, hide } = useTooltip()
  const margin = { left: 8, right: 8, top: 8, bottom: 20 }
  const innerWidth = Math.max(10, width - margin.left - margin.right)
  const trackY = (height - margin.bottom + margin.top) / 2

  const values = items.map((item) => item.value)
  const maxValue = Math.max(...values, median, p75)
  const minValue = Math.min(...values, 0)
  const scale = logScale
    ? scaleLinear().domain([Math.log10(Math.max(1, minValue) || 1), Math.log10(Math.max(10, maxValue))]).range([0, innerWidth])
    : scaleLinear().domain([minValue, maxValue || 1]).range([0, innerWidth])
  const position = (value: number) => (logScale ? scale(Math.log10(Math.max(1, value))) : scale(value))

  /* Точки, севшие в одну координату, расходятся по вертикали: на двадцати
     центрах совпадения обычны, а слипшийся ком скрывает половину сети. */
  const offsets = new Map<string, number>()
  {
    const placed: Array<{ x: number; row: number }> = []
    for (const item of [...items].sort((a, b) => a.value - b.value)) {
      const px = position(item.value)
      let row = 0
      while (placed.some((other) => other.row === row && Math.abs(other.x - px) < 11)) row += 1
      placed.push({ x: px, row })
      offsets.set(item.id, row % 2 === 0 ? -Math.ceil(row / 2) * 9 : Math.ceil(row / 2) * 9)
    }
  }

  return (
    <div ref={ref} className="relative" onMouseLeave={hide}>
      {width > 0 && (
        <svg width={width} height={height}>
          <g transform={`translate(${margin.left},0)`}>
            {/* Межквартильный размах — где лежит середина сети */}
            <rect
              x={position(p25)}
              y={trackY - 11}
              width={Math.max(1, position(p75) - position(p25))}
              height={22}
              fill="var(--panel-3)"
              stroke="var(--rule)"
              rx={2}
            />
            <line x1={0} x2={innerWidth} y1={trackY} y2={trackY} stroke="var(--rule-2)" />
            <line x1={position(median)} x2={position(median)} y1={trackY - 14} y2={trackY + 14} stroke="var(--ink-2)" strokeWidth={1.5} />
            <text x={position(median)} y={height - 4} textAnchor="middle" className="tnum fill-ink-3 text-[10px]">
              медиана {format(median)}
            </text>

            {items.map((item) => {
              const dim = highlight != null && highlight !== item.id
              const cy = trackY + (offsets.get(item.id) ?? 0)
              return (
                <g key={item.id} className={onSelect ? 'cursor-pointer' : ''} onClick={() => onSelect?.(item.id)}>
                  <circle cx={position(item.value)} cy={cy} r={11} fill="transparent"
                    onMouseMove={(event) => {
                      const rect = ref.current!.getBoundingClientRect()
                      show(event.clientX - rect.left, event.clientY - rect.top, (
                        <>
                          <TipTitle color={item.color}>{item.label}</TipTitle>
                          <TipRow label="Значение" value={format(item.value)} strong />
                          <TipRow label="Медиана сети" value={format(median)} />
                        </>
                      ))
                    }}
                  />
                  <circle
                    cx={position(item.value)}
                    cy={cy}
                    r={highlight === item.id ? 6 : 4.5}
                    fill={item.color}
                    stroke="var(--panel)"
                    strokeWidth={2}
                    opacity={dim ? 0.3 : 0.95}
                    className="transition-all duration-150"
                  />
                </g>
              )
            })}
          </g>
        </svg>
      )}
      <Tooltip tip={tip} width={width} />
    </div>
  )
}

/* ── траектория года ──────────────────────────────────────────────────────── */

export interface PaceSeries {
  id: string
  label: string
  color: string
  points: Array<[number, number]>
  dashed?: boolean
  width?: number
}

/**
 * Накопленный темп по месяцам.
 *
 * Сплошная линия — факт за отчётные девять месяцев, пунктир — продолжение
 * текущим темпом, тонкая линия — темп, необходимый для выхода на цель. Пунктир
 * здесь несёт смысл «это прогноз, а не наблюдение», поэтому он только у него:
 * сетка остаётся сплошной.
 */
export function PaceChart({
  series, target, width, height, months = 12, reported = 9, formatValue, yLabel,
}: {
  series: PaceSeries[]
  target?: { value: number; label: string } | null
  width: number
  height: number
  months?: number
  reported?: number
  formatValue: (value: number) => string
  yLabel?: string
}) {
  const margin = { top: 14, right: 16, bottom: 28, left: 52 }
  const innerWidth = Math.max(10, width - margin.left - margin.right)
  const innerHeight = Math.max(10, height - margin.top - margin.bottom)

  const allValues = series.flatMap((s) => s.points.map((p) => p[1])).concat(target ? [target.value] : [])
  const maxValue = Math.max(1, ...allValues)
  const x = scaleLinear().domain([0, months]).range([0, innerWidth])
  const y = scaleLinear().domain([0, maxValue * 1.08]).nice().range([innerHeight, 0])
  const path = d3line<[number, number]>().x((p) => x(p[0])).y((p) => y(p[1]))

  const MONTH_TICKS = [0, 3, 6, 9, 12]
  const MONTH_LABEL: Record<number, string> = { 0: 'янв', 3: 'апр', 6: 'июл', 9: 'сен', 12: 'дек' }

  return (
    <svg width={width} height={height} role="img" aria-label="Накопленный темп по месяцам">
      <g transform={`translate(${margin.left},${margin.top})`}>
        {y.ticks(4).map((tick) => (
          <g key={tick}>
            <line x1={0} x2={innerWidth} y1={y(tick)} y2={y(tick)} stroke="var(--rule)" shapeRendering="crispEdges" />
            <text x={-8} y={y(tick)} textAnchor="end" dominantBaseline="central" className="tnum fill-ink-3 text-[10px]">
              {formatValue(tick)}
            </text>
          </g>
        ))}

        {/* Граница отчётного периода: правее неё все значения — расчёт, а не факт. */}
        <rect x={x(reported)} y={0} width={innerWidth - x(reported)} height={innerHeight} fill="var(--panel-2)" opacity={0.7} />
        <line x1={x(reported)} x2={x(reported)} y1={0} y2={innerHeight} stroke="var(--rule-2)" />
        <text x={x(reported) + 5} y={11} className="fill-ink-3 text-[9.5px]">прогноз</text>

        {target && (
          <>
            <line x1={0} x2={innerWidth} y1={y(target.value)} y2={y(target.value)} stroke="var(--ink-2)" strokeWidth={1} />
            <text x={innerWidth} y={y(target.value) - 5} textAnchor="end" className="fill-ink-2 text-[10px] font-medium">
              {target.label}
            </text>
          </>
        )}

        {series.map((item) => (
          <path
            key={item.id}
            d={path(item.points) ?? ''}
            fill="none"
            stroke={item.color}
            strokeWidth={item.width ?? 2}
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeDasharray={item.dashed ? '5 4' : undefined}
          />
        ))}

        {/* Точка на конце сплошной линии — где сейчас находится факт. */}
        {series.filter((s) => !s.dashed).map((item) => {
          const last = item.points[item.points.length - 1]
          if (!last) return null
          return (
            <circle key={`${item.id}-end`} cx={x(last[0])} cy={y(last[1])} r={4.5} fill={item.color} stroke="var(--panel)" strokeWidth={2} />
          )
        })}

        {MONTH_TICKS.map((tick) => (
          <text key={tick} x={x(tick)} y={innerHeight + 15} textAnchor="middle" className="fill-ink-3 text-[10px]">
            {MONTH_LABEL[tick]}
          </text>
        ))}
        {yLabel && (
          <text x={0} y={-4} className="fill-ink-3 text-[10px]">{yLabel}</text>
        )}
      </g>
    </svg>
  )
}

/* ── дерево слияний ───────────────────────────────────────────────────────── */

/**
 * Дендрограмма иерархической кластеризации.
 *
 * Высота перекладины — расстояние, на котором объединились ветви: чем выше
 * слияние, тем непохожее объединяемое. Линия разреза показывает, где дерево
 * даёт выбранное число кластеров.
 */
export function Dendrogram({
  icoord, dcoord, labels, colorOf, width, height, cutHeight,
}: {
  icoord: number[][]
  dcoord: number[][]
  labels: string[]
  colorOf: (label: string) => string
  width: number
  height: number
  cutHeight?: number
}) {
  const margin = { top: 12, right: 64, bottom: 108, left: 34 }
  const innerWidth = Math.max(10, width - margin.left - margin.right)
  const innerHeight = Math.max(10, height - margin.top - margin.bottom)

  const maxX = Math.max(...icoord.flat())
  const maxY = Math.max(...dcoord.flat())
  const x = scaleLinear().domain([0, maxX]).range([0, innerWidth])
  const y = scaleLinear().domain([0, maxY * 1.05]).range([innerHeight, 0])

  return (
    <svg width={width} height={height} role="img" aria-label="Дендрограмма слияний">
      <g transform={`translate(${margin.left},${margin.top})`}>
        {y.ticks(4).map((tick) => (
          <g key={tick}>
            <line x1={0} x2={innerWidth} y1={y(tick)} y2={y(tick)} stroke="var(--rule)" shapeRendering="crispEdges" />
            <text x={-6} y={y(tick)} textAnchor="end" dominantBaseline="central" className="tnum fill-ink-3 text-[9.5px]">
              {tick}
            </text>
          </g>
        ))}

        {icoord.map((xs, index) => {
          const ys = dcoord[index]
          const above = cutHeight != null && Math.max(...ys) > cutHeight
          const points = xs.map((value, position) => `${x(value)},${y(ys[position])}`).join(' ')
          return (
            <polyline
              key={index}
              points={points}
              fill="none"
              stroke={above ? 'var(--rule-strong)' : 'var(--ink-2)'}
              strokeWidth={above ? 1 : 1.4}
              strokeLinecap="round"
            />
          )
        })}

        {cutHeight != null && (
          <>
            <line x1={0} x2={innerWidth} y1={y(cutHeight)} y2={y(cutHeight)} stroke="var(--st-serious)" strokeWidth={1.5} strokeDasharray="4 3" />
            <text x={innerWidth} y={y(cutHeight) - 5} textAnchor="end" className="text-[10px] font-medium" fill="var(--st-serious)">
              разрез на 5 кластеров
            </text>
          </>
        )}

        {labels.map((label, index) => {
          const px = x(5 + index * 10)
          return (
            <g key={label} transform={`translate(${px},${innerHeight + 8})`}>
              <circle cx={0} cy={0} r={3} fill={colorOf(label)} />
              <text transform="rotate(58)" x={7} y={3} className="fill-ink-2 text-[9px]">
                {label.length > 20 ? `${label.slice(0, 19)}…` : label}
              </text>
            </g>
          )
        })}
      </g>
    </svg>
  )
}

/* ── линии метрик ─────────────────────────────────────────────────────────── */

/** Кривая выбора числа кластеров: одна метрика — одна панель, общая ось X. */
export function MetricLine({
  points, width, height, best, format, domainX,
}: {
  points: Array<[number, number]>
  width: number
  height: number
  best?: number
  format: (value: number) => string
  domainX: [number, number]
}) {
  const margin = { top: 10, right: 10, bottom: 20, left: 34 }
  const innerWidth = Math.max(10, width - margin.left - margin.right)
  const innerHeight = Math.max(10, height - margin.top - margin.bottom)
  const values = points.map((p) => p[1])
  const x = scaleLinear().domain(domainX).range([0, innerWidth])
  const y = scaleLinear().domain([Math.min(...values) * 0.92, Math.max(...values) * 1.06]).nice().range([innerHeight, 0])
  const path = d3line<[number, number]>().x((p) => x(p[0])).y((p) => y(p[1]))

  return (
    <svg width={width} height={height}>
      <g transform={`translate(${margin.left},${margin.top})`}>
        {y.ticks(3).map((tick) => (
          <g key={tick}>
            <line x1={0} x2={innerWidth} y1={y(tick)} y2={y(tick)} stroke="var(--rule)" shapeRendering="crispEdges" />
            <text x={-6} y={y(tick)} textAnchor="end" dominantBaseline="central" className="tnum fill-ink-3 text-[9.5px]">
              {format(tick)}
            </text>
          </g>
        ))}
        <path d={path(points) ?? ''} fill="none" stroke="var(--ink-2)" strokeWidth={2} strokeLinecap="round" />
        {points.map(([px, py]) => {
          const isBest = best === px
          return (
            <g key={px}>
              <circle cx={x(px)} cy={y(py)} r={isBest ? 5 : 3.5} fill={isBest ? 'var(--ink)' : 'var(--ink-2)'} stroke="var(--panel)" strokeWidth={2} />
              <text x={x(px)} y={innerHeight + 14} textAnchor="middle" className="tnum fill-ink-3 text-[9.5px]">
                {px}
              </text>
            </g>
          )
        })}
      </g>
    </svg>
  )
}
