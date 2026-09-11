/**
 * Карта кластеров: первые две главные компоненты признакового пространства.
 *
 * Кластеров пять, а диаграмма рассеяния сравнивает все пары цветов сразу —
 * одного цвета для надёжного различения мало. Поэтому кластер несёт три канала:
 * цвет, форму маркера и оболочку с прямой подписью. Размер точки — величина
 * аудитории по шкале корня (площадь пропорциональна значению).
 */

import { useMemo, useState } from 'react'
import { scaleLinear, scaleSqrt } from 'd3-scale'
import { ClusterMark, Tooltip, TipRow, TipTitle, useTooltip } from './kit'
import { clusterColor, clusterMark } from '../lib/palette'
import { num, pct } from '../lib/format'
import type { ClusterProfile, EmbeddingPoint } from '../lib/types'

/** Выпуклая оболочка (обход Эндрю) — контур вокруг точек одного кластера. */
function hull(points: Array<[number, number]>): Array<[number, number]> {
  if (points.length < 3) return points
  const sorted = [...points].sort((a, b) => a[0] - b[0] || a[1] - b[1])
  const cross = (o: [number, number], a: [number, number], b: [number, number]) =>
    (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
  const build = (list: Array<[number, number]>) => {
    const stack: Array<[number, number]> = []
    for (const point of list) {
      while (stack.length >= 2 && cross(stack[stack.length - 2], stack[stack.length - 1], point) <= 0) stack.pop()
      stack.push(point)
    }
    stack.pop()
    return stack
  }
  return [...build(sorted), ...build([...sorted].reverse())]
}

/**
 * Расширяет контур наружу от центра, чтобы он не резал сами точки.
 *
 * Сглаживание по средним точкам здесь не применяется: оно срезает вершины и
 * выносит крайние центры за пределы собственной оболочки. Мягкость даёт толстый
 * штрих с круглыми стыками, которым контур обводится при отрисовке.
 */
function inflate(path: Array<[number, number]>, padding: number): string {
  if (path.length === 0) return ''
  const cx = path.reduce((sum, point) => sum + point[0], 0) / path.length
  const cy = path.reduce((sum, point) => sum + point[1], 0) / path.length
  const moved = path.map(([x, y]) => {
    const dx = x - cx
    const dy = y - cy
    const length = Math.hypot(dx, dy) || 1
    return [x + (dx / length) * padding, y + (dy / length) * padding] as [number, number]
  })
  return `M${moved.map((point) => `${point[0]} ${point[1]}`).join('L')}${moved.length > 2 ? 'Z' : ''}`
}

export function ClusterScatter({
  points, profiles, explained, width, height, activeCluster, selected, onSelect, onHoverCluster,
}: {
  points: EmbeddingPoint[]
  profiles: ClusterProfile[]
  explained: number[]
  width: number
  height: number
  activeCluster: number | null
  selected: string | null
  onSelect?: (orgId: string) => void
  onHoverCluster?: (cluster: number | null) => void
}) {
  const { tip, show, hide } = useTooltip()
  const [hover, setHover] = useState<string | null>(null)

  const margin = { top: 16, right: 18, bottom: 34, left: 42 }
  const innerWidth = Math.max(10, width - margin.left - margin.right)
  const innerHeight = Math.max(10, height - margin.top - margin.bottom)

  const { x, y, r, byCluster } = useMemo(() => {
    const xs = points.map((p) => p.pc1)
    const ys = points.map((p) => p.pc2)
    const padX = (Math.max(...xs) - Math.min(...xs)) * 0.12 || 1
    const padY = (Math.max(...ys) - Math.min(...ys)) * 0.14 || 1
    const xScale = scaleLinear().domain([Math.min(...xs) - padX, Math.max(...xs) + padX]).range([0, innerWidth])
    const yScale = scaleLinear().domain([Math.min(...ys) - padY, Math.max(...ys) + padY]).range([innerHeight, 0])
    const rScale = scaleSqrt().domain([0, Math.max(...points.map((p) => p.audience_total || 0)) || 1]).range([4.5, 15])

    const groups = new Map<number, EmbeddingPoint[]>()
    for (const point of points) {
      const list = groups.get(point.cluster)
      if (list) list.push(point)
      else groups.set(point.cluster, [point])
    }
    return { x: xScale, y: yScale, r: rScale, byCluster: groups }
  }, [points, innerWidth, innerHeight])

  const xTicks = x.ticks(6)
  const yTicks = y.ticks(5)

  return (
    <div className="relative" onMouseLeave={() => { hide(); setHover(null); onHoverCluster?.(null) }}>
      <svg width={width} height={height} role="img" aria-label="Карта кластеров в пространстве главных компонент">
        <g transform={`translate(${margin.left},${margin.top})`}>
          {yTicks.map((tick) => (
            <line key={`y${tick}`} x1={0} x2={innerWidth} y1={y(tick)} y2={y(tick)} stroke="var(--rule)" shapeRendering="crispEdges" />
          ))}
          {xTicks.map((tick) => (
            <line key={`x${tick}`} y1={0} y2={innerHeight} x1={x(tick)} x2={x(tick)} stroke="var(--rule)" shapeRendering="crispEdges" />
          ))}
          {/* Нулевые оси главных компонент: центр облака, точка отсчёта «средний центр». */}
          <line x1={x(0)} x2={x(0)} y1={0} y2={innerHeight} stroke="var(--rule-2)" strokeWidth={1} />
          <line x1={0} x2={innerWidth} y1={y(0)} y2={y(0)} stroke="var(--rule-2)" strokeWidth={1} />

          {yTicks.map((tick) => (
            <text key={`yl${tick}`} x={-8} y={y(tick)} textAnchor="end" dominantBaseline="central" className="tnum fill-ink-3 text-[10px]">
              {tick}
            </text>
          ))}
          {xTicks.map((tick) => (
            <text key={`xl${tick}`} x={x(tick)} y={innerHeight + 15} textAnchor="middle" className="tnum fill-ink-3 text-[10px]">
              {tick}
            </text>
          ))}

          {/* Оболочки кластеров.

              Контур обводится толстым штрихом с круглыми стыками, а не рисуется
              как есть: у кластера из двух центров «оболочки» не существует, а у
              вытянутого втроём она вырождается в полоску. Толстый штрих даёт всем
              группам одинаково читаемое пятно. */}
          {[...byCluster.entries()].map(([cluster, members]) => {
            const dim = activeCluster != null && activeCluster !== cluster
            const path = inflate(hull(members.map((m) => [x(m.pc1), y(m.pc2)] as [number, number])), 6)
            if (!path) return null
            const fill = `color-mix(in oklab, ${clusterColor(cluster)} ${dim ? 3 : 8}%, transparent)`
            const edge = `color-mix(in oklab, ${clusterColor(cluster)} ${dim ? 10 : 30}%, transparent)`
            return (
              <g key={`hull${cluster}`} className="transition-opacity duration-200" style={{ pointerEvents: 'none' }}>
                <path d={path} fill="none" stroke={edge} strokeWidth={38} strokeLinejoin="round" strokeLinecap="round" />
                <path d={path} fill={fill} stroke={fill} strokeWidth={36} strokeLinejoin="round" strokeLinecap="round" />
              </g>
            )
          })}

          {/* Точки */}
          {points.map((point) => {
            const dim = activeCluster != null && activeCluster !== point.cluster
            const isSelected = selected === point.org_id
            const isHover = hover === point.org_id
            const radius = r(point.audience_total || 0)
            return (
              <g
                key={point.org_id}
                className="cursor-pointer transition-opacity duration-200"
                opacity={dim ? 0.22 : 1}
                onMouseEnter={() => { setHover(point.org_id); onHoverCluster?.(point.cluster) }}
                onMouseMove={(event) => {
                  const rect = event.currentTarget.ownerSVGElement!.parentElement!.getBoundingClientRect()
                  const profile = profiles.find((p) => p.cluster_id === point.cluster)
                  show(
                    event.clientX - rect.left,
                    event.clientY - rect.top,
                    <>
                      <TipTitle color={clusterColor(point.cluster)}>{point.name}</TipTitle>
                      <TipRow label="Модель" value={profile?.name ?? `Кластер ${point.cluster + 1}`} />
                      <TipRow label="Аудитория" value={`${num(point.audience_total)} чел.`} strong />
                      <TipRow label="Силуэт" value={point.silhouette.toFixed(2)} />
                    </>,
                  )
                }}
                onClick={() => onSelect?.(point.org_id)}
              >
                {/* Невидимая мишень: попасть в восьмипиксельную точку мышью тяжело. */}
                <circle cx={x(point.pc1)} cy={y(point.pc2)} r={Math.max(radius + 8, 14)} fill="transparent" />
                {(isSelected || isHover) && (
                  <circle
                    cx={x(point.pc1)}
                    cy={y(point.pc2)}
                    r={radius + 6}
                    fill="none"
                    stroke={clusterColor(point.cluster)}
                    strokeWidth={1}
                    opacity={0.55}
                  />
                )}
                <ClusterMark
                  shape={clusterMark(point.cluster)}
                  x={x(point.pc1)}
                  y={y(point.pc2)}
                  r={radius}
                  fill={clusterColor(point.cluster)}
                  ring="var(--panel)"
                  strokeWidth={2}
                />
                {(isSelected || isHover) && (
                  <text
                    x={x(point.pc1)}
                    y={y(point.pc2) - radius - 10}
                    textAnchor="middle"
                    className="fill-ink text-[11px] font-medium"
                    style={{ paintOrder: 'stroke', stroke: 'var(--panel)', strokeWidth: 3.5, strokeLinejoin: 'round' }}
                  >
                    {point.name}
                  </text>
                )}
              </g>
            )
          })}
        </g>

        <text x={width - margin.right} y={height - 4} textAnchor="end" className="fill-ink-3 text-[10px]">
          PC1 · {pct(explained[0], 0)} дисперсии
        </text>
        <text
          x={-(margin.top + innerHeight / 2)}
          y={11}
          transform="rotate(-90)"
          textAnchor="middle"
          className="fill-ink-3 text-[10px]"
        >
          PC2 · {pct(explained[1], 0)}
        </text>
      </svg>
      <Tooltip tip={tip} width={width} />
    </div>
  )
}
