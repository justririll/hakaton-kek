/**
 * Диаграмма «два показателя против медиан сети».
 *
 * Линии медиан делят поле на четыре четверти, и каждая из них имеет
 * управленческое имя — так точка читается как диагноз, а не как координата.
 * Кластер кодируется цветом и формой одновременно: пяти цветов на диаграмме
 * рассеяния для надёжного различения мало.
 */

import { useState } from 'react'
import { scaleLinear, scaleSqrt } from 'd3-scale'
import { ClusterMark, Tooltip, TipRow, TipTitle, useTooltip } from './kit'
import { clusterColor, clusterMark } from '../lib/palette'
import { num } from '../lib/format'

export interface QuadrantPoint {
  id: string
  label: string
  cluster: number
  x: number
  y: number
  size: number
}

export function QuadrantScatter({
  points, width, height, xLabel, yLabel, xFormat, yFormat, quadrants, onSelect, selected, clamp,
}: {
  points: QuadrantPoint[]
  width: number
  height: number
  xLabel: string
  yLabel: string
  xFormat: (value: number) => string
  yFormat: (value: number) => string
  /** Подписи четвертей: слева-снизу, справа-снизу, слева-сверху, справа-сверху. */
  quadrants: [string, string, string, string]
  onSelect?: (id: string) => void
  selected?: string | null
  /** Верхняя отсечка по осям: единичные выбросы иначе сжимают всё облако в угол. */
  clamp?: { x?: number; y?: number }
}) {
  const { tip, show, hide } = useTooltip()
  const [hover, setHover] = useState<string | null>(null)

  const margin = { top: 18, right: 16, bottom: 40, left: 56 }
  const innerWidth = Math.max(10, width - margin.left - margin.right)
  const innerHeight = Math.max(10, height - margin.top - margin.bottom)

  const xs = points.map((p) => Math.min(p.x, clamp?.x ?? Infinity))
  const ys = points.map((p) => Math.min(p.y, clamp?.y ?? Infinity))
  const x = scaleLinear().domain([0, Math.max(...xs) * 1.08 || 1]).nice().range([0, innerWidth])
  const y = scaleLinear().domain([0, Math.max(...ys) * 1.08 || 1]).nice().range([innerHeight, 0])
  const r = scaleSqrt().domain([0, Math.max(...points.map((p) => p.size)) || 1]).range([4.5, 14])

  const median = (values: number[]) => {
    const sorted = [...values].sort((a, b) => a - b)
    const middle = Math.floor(sorted.length / 2)
    return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2
  }
  const mx = median(points.map((p) => p.x))
  const my = median(points.map((p) => p.y))

  const corners: Array<{ text: string; dx: number; dy: number; anchor: 'start' | 'end' }> = [
    { text: quadrants[0], dx: 6, dy: innerHeight - 8, anchor: 'start' },
    { text: quadrants[1], dx: innerWidth - 6, dy: innerHeight - 8, anchor: 'end' },
    { text: quadrants[2], dx: 6, dy: 13, anchor: 'start' },
    { text: quadrants[3], dx: innerWidth - 6, dy: 13, anchor: 'end' },
  ]

  return (
    <div className="relative" onMouseLeave={() => { hide(); setHover(null) }}>
      <svg width={width} height={height} role="img" aria-label={`${xLabel} против ${yLabel}`}>
        <g transform={`translate(${margin.left},${margin.top})`}>
          {y.ticks(4).map((tick) => (
            <g key={`y${tick}`}>
              <line x1={0} x2={innerWidth} y1={y(tick)} y2={y(tick)} stroke="var(--rule)" shapeRendering="crispEdges" />
              <text x={-8} y={y(tick)} textAnchor="end" dominantBaseline="central" className="tnum fill-ink-3 text-[10px]">
                {yFormat(tick)}
              </text>
            </g>
          ))}
          {x.ticks(5).map((tick) => (
            <g key={`x${tick}`}>
              <line x1={x(tick)} x2={x(tick)} y1={0} y2={innerHeight} stroke="var(--rule)" shapeRendering="crispEdges" />
              <text x={x(tick)} y={innerHeight + 15} textAnchor="middle" className="tnum fill-ink-3 text-[10px]">
                {xFormat(tick)}
              </text>
            </g>
          ))}

          {/* Медианы сети — границы четвертей */}
          <line x1={x(mx)} x2={x(mx)} y1={0} y2={innerHeight} stroke="var(--rule-strong)" strokeWidth={1} />
          <line x1={0} x2={innerWidth} y1={y(my)} y2={y(my)} stroke="var(--rule-strong)" strokeWidth={1} />

          {corners.map((corner) => (
            // Обводка цветом подложки: подпись четверти лежит под точками и без
            // неё тонет в облаке.
            <text
              key={corner.text}
              x={corner.dx}
              y={corner.dy}
              textAnchor={corner.anchor}
              className="fill-ink-3 text-[10px]"
              style={{ paintOrder: 'stroke', stroke: 'var(--panel)', strokeWidth: 3, strokeLinejoin: 'round' }}
            >
              {corner.text}
            </text>
          ))}

          {points.map((point) => {
            const clampedX = clamp?.x != null && point.x > clamp.x
            const clampedY = clamp?.y != null && point.y > clamp.y
            const px = x(Math.min(point.x, clamp?.x ?? Infinity))
            const py = y(Math.min(point.y, clamp?.y ?? Infinity))
            const radius = r(point.size)
            const active = hover === point.id || selected === point.id
            return (
              <g
                key={point.id}
                className="cursor-pointer"
                onMouseEnter={() => setHover(point.id)}
                onMouseMove={(event) => {
                  const rect = event.currentTarget.ownerSVGElement!.parentElement!.getBoundingClientRect()
                  show(event.clientX - rect.left, event.clientY - rect.top, (
                    <>
                      <TipTitle color={clusterColor(point.cluster)}>{point.label}</TipTitle>
                      <TipRow label={xLabel} value={xFormat(point.x)} strong />
                      <TipRow label={yLabel} value={yFormat(point.y)} strong />
                      <TipRow label="Аудитория" value={`${num(point.size)} чел.`} />
                    </>
                  ))
                }}
                onClick={() => onSelect?.(point.id)}
              >
                <circle cx={px} cy={py} r={Math.max(radius + 8, 14)} fill="transparent" />
                {active && <circle cx={px} cy={py} r={radius + 6} fill="none" stroke={clusterColor(point.cluster)} opacity={0.55} />}
                <ClusterMark
                  shape={clusterMark(point.cluster)}
                  x={px}
                  y={py}
                  r={radius}
                  fill={clusterColor(point.cluster)}
                  ring="var(--panel)"
                  strokeWidth={2}
                />
                {(clampedX || clampedY) && (
                  // Значение вышло за обрезку шкалы: галочка говорит, что точка
                  // стоит не там, где её настоящее место.
                  <path
                    d={clampedY
                      ? `M${px - 4} ${py - radius - 4}L${px} ${py - radius - 8}L${px + 4} ${py - radius - 4}`
                      : `M${px + radius + 4} ${py - 4}L${px + radius + 8} ${py}L${px + radius + 4} ${py + 4}`}
                    fill="none"
                    stroke={clusterColor(point.cluster)}
                    strokeWidth={1.6}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                )}
                {active && (
                  <text
                    x={px}
                    y={py - radius - 9}
                    textAnchor="middle"
                    className="fill-ink text-[11px] font-medium"
                    style={{ paintOrder: 'stroke', stroke: 'var(--panel)', strokeWidth: 3.5, strokeLinejoin: 'round' }}
                  >
                    {point.label}
                  </text>
                )}
              </g>
            )
          })}
        </g>
        <text x={width - margin.right} y={height - 4} textAnchor="end" className="fill-ink-3 text-[10px]">{xLabel}</text>
        <text x={-(margin.top + innerHeight / 2)} y={11} transform="rotate(-90)" textAnchor="middle" className="fill-ink-3 text-[10px]">
          {yLabel}
        </text>
      </svg>
      <Tooltip tip={tip} width={width} />
    </div>
  )
}
