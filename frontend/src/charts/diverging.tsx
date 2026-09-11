/** Формы для знаковых величин: отклонения по z и матрицы совпадений. */

import { Tooltip, TipRow, TipTitle, useMeasure, useTooltip } from './kit'
import { SEQ } from '../lib/palette'

/**
 * Отклонения признаков кластера от средней сети, в стандартных отклонениях.
 *
 * Форма — «леденец»: ноль по центру, длина плеча = величина отклонения, сторона =
 * знак. Столбцы здесь читались бы как величина, а не как отклонение от нормы.
 */
export function ZLollipop({
  items, color, max, rowHeight = 26, labelWidth = 186,
}: {
  items: Array<{ label: string; value: number; hint?: string }>
  color: string
  max?: number
  rowHeight?: number
  labelWidth?: number
}) {
  const limit = max ?? Math.max(1, ...items.map((item) => Math.abs(item.value))) * 1.12
  const { ref, width } = useMeasure<HTMLDivElement>()
  const track = Math.max(60, width - labelWidth - 46)
  const half = track / 2

  return (
    <div ref={ref} className="w-full">
      <ul>
        {items.map((item) => {
          const offset = (Math.max(-limit, Math.min(limit, item.value)) / limit) * half
          return (
            <li key={item.label} className="flex items-center gap-3" style={{ height: rowHeight }} title={item.hint}>
              <span className="shrink-0 truncate text-[12px] text-ink-2" style={{ width: labelWidth }}>
                {item.label}
              </span>
              <span className="relative shrink-0" style={{ width: track, height: rowHeight }}>
                <span className="absolute top-0 bottom-0 left-1/2 w-px -translate-x-1/2 bg-rule-2" />
                <span
                  className="absolute top-1/2 h-[2px] -translate-y-1/2 rounded-full"
                  style={{
                    left: offset >= 0 ? half : half + offset,
                    width: Math.abs(offset),
                    background: color,
                  }}
                />
                <span
                  className="absolute top-1/2 size-[9px] -translate-x-1/2 -translate-y-1/2 rounded-full"
                  style={{ left: half + offset, background: color, boxShadow: '0 0 0 2px var(--panel)' }}
                />
              </span>
              <span className="tnum w-[42px] shrink-0 text-right text-[11.5px] font-medium text-ink">
                {item.value > 0 ? '+' : item.value < 0 ? '−' : ''}
                {Math.abs(item.value).toFixed(2)}
              </span>
            </li>
          )
        })}
      </ul>
      <div className="mt-1 flex text-[10.5px] text-ink-3" style={{ paddingLeft: labelWidth + 12 }}>
        <span style={{ width: track }} className="flex justify-between">
          <span>−{limit.toFixed(1)} σ</span>
          <span>среднее по сети</span>
          <span>+{limit.toFixed(1)} σ</span>
        </span>
      </div>
    </div>
  )
}

/**
 * Тепловая карта.
 *
 * Шкала последовательная — один тон от светлого к тёмному: радуга на величине
 * выдумывает границы там, где их нет. Значение дублируется в подсказке и в
 * табличном представлении, поэтому цвет не остаётся единственным носителем.
 */
export function Heatmap({
  rows, columns, value, format, cellMin = 18, cellMax = 40, rowLabelWidth = 120, title, asTable = false,
}: {
  rows: Array<{ id: string; label: string }>
  columns: Array<{ id: string; label: string }>
  value: (rowId: string, columnId: string) => number
  format: (value: number) => string
  cellMin?: number
  cellMax?: number
  rowLabelWidth?: number
  title?: string
  /** Табличный двойник: тот же набор значений без опоры на цвет. */
  asTable?: boolean
}) {
  const { ref, width } = useMeasure<HTMLDivElement>()
  const { tip, show, hide } = useTooltip()
  // Клетка не растягивается на всю ширину панели: на двадцати строках это
  // превращает матрицу в километровое полотно.
  const cell = Math.min(cellMax, Math.max(cellMin, Math.floor((width - rowLabelWidth - 2) / Math.max(1, columns.length))))

  if (asTable) {
    return (
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-[11.5px]">
          <caption className="sr-only">{title ?? 'Значения'}</caption>
          <thead>
            <tr className="border-b border-rule">
              <th scope="col" className="eyebrow sticky left-0 bg-panel py-1.5 pr-3 text-left font-medium">Строка</th>
              {columns.map((column) => (
                <th key={column.id} scope="col" className="eyebrow py-1.5 pl-3 text-right font-medium whitespace-nowrap">
                  {column.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-rule">
            {rows.map((row) => (
              <tr key={row.id} className="transition-colors hover:bg-panel-2">
                <th scope="row" className="sticky left-0 bg-panel py-1.5 pr-3 text-left font-medium whitespace-nowrap text-ink">
                  {row.label}
                </th>
                {columns.map((column) => {
                  const raw = value(row.id, column.id)
                  return (
                    <td key={column.id} className={`tnum py-1.5 pl-3 text-right ${raw > 0.001 ? 'text-ink-2' : 'text-ink-3'}`}>
                      {format(raw)}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  }

  const step = (v: number) => {
    const index = Math.min(SEQ.length - 1, Math.max(0, Math.round(v * (SEQ.length - 1))))
    return v <= 0.001 ? 'var(--panel-2)' : SEQ[index]
  }

  return (
    <div ref={ref} className="relative overflow-x-auto" onMouseLeave={hide}>
      <div style={{ width: rowLabelWidth + cell * columns.length }}>
        <div className="flex" style={{ paddingLeft: rowLabelWidth }}>
          {columns.map((column) => (
            <div
              key={column.id}
              className="shrink-0 text-[9.5px] text-ink-3"
              style={{ width: cell, height: 62, writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}
              title={column.label}
            >
              <span className="block truncate" style={{ maxHeight: 60 }}>{column.label}</span>
            </div>
          ))}
        </div>
        {rows.map((row) => (
          <div key={row.id} className="flex items-center">
            <div className="shrink-0 truncate pr-2 text-[11px] text-ink-2" style={{ width: rowLabelWidth }} title={row.label}>
              {row.label}
            </div>
            {columns.map((column) => {
              const raw = value(row.id, column.id)
              return (
                <div
                  key={column.id}
                  className="shrink-0 border border-panel transition-[outline] duration-100 hover:outline hover:outline-ink"
                  style={{ width: cell, height: cell, background: step(raw) }}
                  onMouseMove={(event) => {
                    const rect = ref.current!.getBoundingClientRect()
                    show(
                      event.clientX - rect.left,
                      event.clientY - rect.top,
                      <>
                        <TipTitle>{title ?? 'Значение'}</TipTitle>
                        <TipRow label="Строка" value={row.label} />
                        <TipRow label="Столбец" value={column.label} />
                        <TipRow label="Значение" value={format(raw)} strong />
                      </>,
                    )
                  }}
                />
              )
            })}
          </div>
        ))}
      </div>
      <Tooltip tip={tip} width={width} />
    </div>
  )
}

/** Легенда последовательной шкалы: без неё тепловая карта не читается. */
export function SeqLegend({ from, to, caption }: { from: string; to: string; caption?: string }) {
  return (
    <div className="flex items-center gap-2 text-[10.5px] text-ink-3">
      <span>{from}</span>
      <span className="flex h-2.5 overflow-hidden rounded-[2px]">
        {SEQ.map((color) => (
          <span key={color} className="w-5" style={{ background: color }} />
        ))}
      </span>
      <span>{to}</span>
      {caption && <span className="ml-1">· {caption}</span>}
    </div>
  )
}
