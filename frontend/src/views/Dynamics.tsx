/** Динамика: база 2025 → факт девяти месяцев → прогноз года → цель. */

import { useMemo, useState } from 'react'
import { useData } from '../lib/store'
import { Page, Band } from '../ui/Page'
import { Panel, Segmented, StatusTag, Chip, InfoDot } from '../ui/primitives'
import { Icon } from '../ui/Icon'
import { ChartBox } from '../charts/kit'
import { PaceChart } from '../charts/shapes'
import { RankedBars, PlanMeter } from '../charts/bars'
import { StripPlot } from '../charts/shapes'
import { STATUS_META, clusterColor } from '../lib/palette'
import { compact, dec, delta, money, num, pct, plural, withUnit } from '../lib/format'
import type { DynamicsRow } from '../lib/types'

const STATUS_ICON = { good: 'check', warn: 'alert', crit: 'alert', serious: 'alert', none: 'minus' } as const

const METRIC_COLUMN: Record<DynamicsRow['key'], string> = {
  audience: 'audience_total',
  formats: 'supply_total',
  products: 'products_total',
  revenue: 'revenue_total',
}

export function Dynamics() {
  const { data, derived } = useData()
  const { overview, plan, organizations } = data
  const [metric, setMetric] = useState<DynamicsRow['key']>('formats')
  const [sort, setSort] = useState<'completion' | 'gap' | 'fact'>('completion')

  const row = overview.dynamics.find((item) => item.key === metric)!
  const formatValue = (value: number) => (row.unit === '₽' ? money(value) : compact(value))

  /* Накопленная кривая: помесячной разбивки в отчётности нет, поэтому факт
     раскладывается ровным темпом — это оценка хода, а не наблюдение. */
  const pace = useMemo(() => {
    const target = row.target_2026 ?? row.run_rate_year
    return {
      fact: Array.from({ length: 10 }, (_, month) => [month, (row.fact_ytd / 9) * month] as [number, number]),
      forecast: [[9, row.fact_ytd], [12, row.run_rate_year]] as Array<[number, number]>,
      required: row.target_2026 ? ([[9, row.fact_ytd], [12, target]] as Array<[number, number]>) : null,
      target,
    }
  }, [row])

  const planRows = useMemo(() => {
    const rows = [...plan]
    rows.sort((a, b) => {
      if (sort === 'fact') return b.fact_ytd - a.fact_ytd
      if (sort === 'gap') return (a.forecast_gap ?? 0) - (b.forecast_gap ?? 0)
      return (a.completion ?? 99) - (b.completion ?? 99)
    })
    return rows
  }, [plan, sort])

  const column = METRIC_COLUMN[metric]
  const ranked = useMemo(
    () =>
      [...organizations]
        .sort((a, b) => (b[column] as number) - (a[column] as number))
        .map((org) => ({
          id: org.org_id,
          label: org.short_name,
          value: org[column] as number,
          color: clusterColor(org.cluster),
        })),
    [organizations, column],
  )

  const values = ranked.map((item) => item.value).sort((a, b) => a - b)
  const quantile = (q: number) => values[Math.min(values.length - 1, Math.floor(q * (values.length - 1)))]

  return (
    <Page
      eyebrow="Динамика · отчётный период 9 месяцев"
      title="Куда движется сеть"
      lede={
        <>
          Отчётность годовая, помесячной разбивки в формах нет: факт накоплен за девять месяцев,
          а база — за полный 2025 год. Поэтому рядом стоят два числа — прямой накопленный факт
          и приведённый к году по текущему темпу. Там, где базы нет, витрина говорит об этом прямо,
          а не подставляет ноль.
        </>
      }
      actions={
        <Segmented
          ariaLabel="Показатель"
          value={metric}
          onChange={setMetric}
          options={overview.dynamics.map((item) => ({ value: item.key, label: item.label }))}
        />
      }
    >
      {/* ── выбранный показатель ─────────────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
        <Panel
          eyebrow={`${row.label} · накопленным итогом`}
          title={
            row.baseline_2025 != null
              ? `Приведённый к году темп: ${delta(row.growth_year)} к 2025-му`
              : 'Базы 2025 года по этому показателю нет'
          }
          subtitle={
            row.baseline_2025 != null
              ? `Сопоставимый круг — ${row.baseline_orgs} ${plural(row.baseline_orgs, ['центр', 'центра', 'центров'])} с заполненной базой (${pct(row.baseline_coverage)} сети)`
              : 'Формы 2025 года по этому показателю не заполнены ни у одного центра — сравнивать не с чем, поэтому показан только текущий уровень и его продолжение'
          }
          footnote={
            row.baseline_2025 != null ? (
              <>
                Прямое сопоставление девяти месяцев с полным годом даёт {delta(row.growth_ytd)} — оно
                заведомо занижено. Содержательная величина — приведённый темп {delta(row.growth_year)}.
              </>
            ) : (
              'Пунктир справа от сентября — продолжение текущего темпа, а не наблюдение.'
            )
          }
        >
          <ChartBox height={250}>
            {({ width, height }) => (
              <PaceChart
                width={width}
                height={height}
                formatValue={(value) => (row.unit === '₽' ? compact(value) : num(Math.round(value)))}
                target={row.target_2026 ? { value: row.target_2026, label: `цель ${num(row.target_2026)}` } : null}
                series={[
                  { id: 'fact', label: 'Факт', color: 'var(--ink)', points: pace.fact },
                  { id: 'forecast', label: 'Текущий темп', color: 'var(--c-0)', points: pace.forecast, dashed: true },
                  ...(pace.required
                    ? [{ id: 'required', label: 'Нужный темп', color: 'var(--ink-3)', points: pace.required, dashed: true, width: 1.5 }]
                    : []),
                ]}
              />
            )}
          </ChartBox>
          <ul className="mt-2 flex flex-wrap items-center gap-x-5 gap-y-1.5 text-[11.5px] text-ink-2">
            <li className="flex items-center gap-1.5"><span className="h-[2px] w-5 rounded-full bg-ink" />Факт, 9 месяцев</li>
            <li className="flex items-center gap-1.5">
              <span className="h-[2px] w-5" style={{ background: 'var(--c-0)', maskImage: 'repeating-linear-gradient(90deg,#000 0 5px,transparent 5px 9px)' }} />
              Продолжение текущим темпом
            </li>
            {pace.required && (
              <li className="flex items-center gap-1.5">
                <span className="h-[2px] w-5" style={{ background: 'var(--ink-3)', maskImage: 'repeating-linear-gradient(90deg,#000 0 5px,transparent 5px 9px)' }} />
                Темп, нужный для цели
              </li>
            )}
          </ul>
        </Panel>

        <Panel eyebrow="Четыре точки" title="Как читается год" subtitle="База, накопленный факт, продолжение темпа и цель — в одних единицах">
          <ol className="divide-y divide-rule">
            {[
              {
                label: 'База 2025 года',
                value: row.baseline_2025,
                note: row.baseline_2025 != null
                  ? `по ${row.baseline_orgs} ${plural(row.baseline_orgs, ['центру', 'центрам', 'центрам'])} с заполненной формой`
                  : 'форма не заполнена — сравнивать не с чем',
              },
              {
                label: 'Факт, 9 месяцев 2026',
                value: row.fact_ytd,
                note: row.fact_comparable != null
                  ? `по сопоставимому кругу — ${withUnit(row.fact_comparable, row.unit)}`
                  : 'по всем двадцати центрам',
              },
              {
                label: 'Прогноз года по текущему темпу',
                value: row.run_rate_year,
                note: 'факт, умноженный на 12/9 — расчёт, а не наблюдение',
              },
              {
                label: 'Цель 2026 года',
                value: row.target_2026,
                note: row.target_2026 != null
                  ? 'задана Формой 1: прирост числа мероприятий к базе'
                  : 'плановой величины для этого показателя в формах нет',
              },
            ].map((item, index) => (
              <li key={item.label} className="flex items-start gap-3 py-3 first:pt-0 last:pb-0">
                <span className="eyebrow mt-1 w-4 shrink-0 tabular-nums">{index + 1}</span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5">
                    <span className="text-[12.5px] text-ink-2">{item.label}</span>
                    <span className={`tnum text-[17px] font-semibold ${item.value == null ? 'text-ink-3' : 'text-ink'}`}>
                      {item.value == null ? 'нет данных' : withUnit(item.value, row.unit)}
                    </span>
                  </div>
                  <p className="mt-0.5 text-[11px] leading-snug text-ink-3">{item.note}</p>
                </div>
              </li>
            ))}
          </ol>
        </Panel>
      </div>

      {/* ── исполнение по центрам ────────────────────────────────────────── */}
      <Band
        title="Годовой план по каждому центру"
        note="Цель — прирост числа мероприятий к базе 2025 года, заданный Формой 1"
      >
        <Panel
          eyebrow="Факт против цели"
          title="Двадцать центров в порядке исполнения"
          subtitle="Заливка — накопленный факт, вертикаль — цель года, чёрная засечка — прогноз по текущему темпу"
          actions={
            <Segmented
              ariaLabel="Сортировка"
              size="sm"
              value={sort}
              onChange={setSort}
              options={[
                { value: 'completion', label: 'По исполнению' },
                { value: 'gap', label: 'По разрыву' },
                { value: 'fact', label: 'По объёму' },
              ]}
            />
          }
          footnote="Два центра идут без базы: прироста к 2025 году в их формах нет, поэтому цель для них не считается."
        >
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] border-collapse text-[12.5px]">
              <thead>
                <tr className="border-b border-rule text-left">
                  {['Центр', 'Исполнение цели', '%', 'Факт', 'Цель', 'Прогноз', 'Темп, ед./мес.', 'Статус'].map((head, index) => (
                    <th
                      key={head}
                      className={`eyebrow pb-2 font-medium ${index >= 2 && index <= 6 ? 'pl-4 text-right' : ''} ${index === 7 ? 'pl-5' : ''}`}
                    >
                      {head}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-rule">
                {planRows.map((item) => {
                  const meta = STATUS_META[item.status]
                  const org = derived.byId.get(item.org_id)
                  return (
                    <tr key={item.org_id} className="group transition-colors hover:bg-panel-2">
                      <td className="py-2 pr-3">
                        <div className="flex items-center gap-2">
                          <span
                            aria-hidden
                            className="size-2 shrink-0 rounded-full"
                            style={{ background: org ? clusterColor(org.cluster) : 'var(--rule-2)' }}
                          />
                          <span className="truncate font-medium text-ink" title={org?.full_name}>{item.short_name}</span>
                        </div>
                      </td>
                      <td className="w-[190px] py-2 pr-4">
                        {item.completion == null ? (
                          <div className="hatch h-2 rounded-full border border-rule" title="Цель не задана" />
                        ) : (
                          <PlanMeter
                            completion={item.completion}
                            forecastShare={item.target_2026 ? (item.run_rate_forecast ?? 0) / item.target_2026 : null}
                            color={meta?.color ?? 'var(--st-none)'}
                            height={7}
                          />
                        )}
                      </td>
                      <td className="tnum py-2 pr-3 pl-4 text-right font-medium text-ink">
                        {item.status === 'без базы' ? '—' : pct(item.completion)}
                      </td>
                      <td className="tnum py-2 pr-3 pl-4 text-right text-ink-2">{num(item.fact_ytd)}</td>
                      <td className="tnum py-2 pr-3 text-right text-ink-2">{item.target_2026 == null ? '—' : dec(item.target_2026)}</td>
                      <td className="tnum py-2 pr-3 text-right text-ink-2">{item.run_rate_forecast == null ? '—' : dec(item.run_rate_forecast)}</td>
                      <td className="tnum py-2 pr-3 text-right text-ink-2">
                        {item.current_monthly_rate == null ? '—' : dec(item.current_monthly_rate, 1)}
                        {item.required_monthly_rate != null && item.required_monthly_rate > 0 && (
                          <span className="text-ink-3"> / {dec(item.required_monthly_rate, 1)}</span>
                        )}
                      </td>
                      <td className="py-2 pl-5">
                        <StatusTag
                          label={meta?.label ?? item.status}
                          color={meta?.color ?? 'var(--st-none)'}
                          icon={STATUS_ICON[meta?.tone ?? 'none']}
                        />
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          <p className="mt-3 flex items-center gap-1.5 text-[11.5px] text-ink-3">
            <Icon name="info" size={12} />
            В колонке «темп» слева — текущий факт в месяц, справа — сколько нужно в оставшиеся три месяца,
            чтобы выйти на цель.
          </p>
        </Panel>
      </Band>

      {/* ── распределение показателя ─────────────────────────────────────── */}
      <Band title={`Разброс: ${row.label.toLowerCase()}`} note="Каждая точка — центр, полоса — межквартильный размах сети">
        <div className="grid items-start grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)]">
          <Panel
            eyebrow="Распределение по сети"
            title="Половина центров укладывается в серую полосу"
            subtitle="Двадцати наблюдений мало для гистограммы: точки показывают и разброс, и выбросы"
          >
            <StripPlot
              items={ranked}
              median={quantile(0.5)}
              p25={quantile(0.25)}
              p75={quantile(0.75)}
              format={formatValue}
              height={78}
            />
            <dl className="mt-3 grid grid-cols-4 gap-3 border-t border-rule pt-3">
              {[
                ['Минимум', values[0]],
                ['25-й процентиль', quantile(0.25)],
                ['Медиана', quantile(0.5)],
                ['Максимум', values[values.length - 1]],
              ].map(([label, value]) => (
                <div key={label as string}>
                  <dt className="text-[10.5px] leading-snug text-ink-3">{label}</dt>
                  <dd className="tnum mt-0.5 text-[13px] font-medium text-ink">{formatValue(value as number)}</dd>
                </div>
              ))}
            </dl>
          </Panel>

          <Panel
            eyebrow="Рейтинг"
            title={`${row.label}: от большего к меньшему`}
            subtitle="Цвет столбца — аудиторная модель центра"
            actions={<InfoDot text="Цвет повторяет кластер из раздела «Кластеры»: рядом стоят центры с похожей аудиторной моделью." />}
          >
            <RankedBars items={ranked} format={formatValue} labelWidth={178} valueWidth={78} />
          </Panel>
        </div>
      </Band>

      {/* ── показатели без базы ──────────────────────────────────────────── */}
      <Band title="Что можно и чего нельзя сравнить" note="Покрытие базы 2025 года по каждому показателю">
        <div className="stagger grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {overview.dynamics.map((item) => (
            <button
              key={item.key}
              onClick={() => setMetric(item.key)}
              className={`panel flex flex-col gap-2.5 p-4 text-left shadow-card transition-[border-color,transform] duration-150 hover:-translate-y-0.5 hover:border-rule-strong ${
                item.key === metric ? 'border-rule-strong' : ''
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <span className="text-[13px] font-medium text-ink">{item.label}</span>
                {item.baseline_2025 != null ? (
                  <Chip color="var(--st-good)" mark>база есть</Chip>
                ) : (
                  <Chip color="var(--st-none)" mark>базы нет</Chip>
                )}
              </div>
              <div className="tnum text-[22px] font-semibold text-ink">{withUnit(item.fact_ytd, item.unit)}</div>
              <p className="text-[11.5px] leading-snug text-ink-3">
                {item.baseline_2025 != null ? (
                  <>
                    База {withUnit(item.baseline_2025, item.unit)} у {item.baseline_orgs} центров.
                    Приведённый темп {delta(item.growth_year)}.
                  </>
                ) : (
                  <>Форма 2025 года не заполнена ни у одного центра — прирост не определён.</>
                )}
              </p>
              <div className="mt-auto h-1 w-full overflow-hidden rounded-full bg-panel-3">
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${item.baseline_coverage * 100}%`,
                    background: item.baseline_coverage > 0 ? 'var(--st-good)' : 'transparent',
                  }}
                />
              </div>
              <span className="text-[10.5px] text-ink-3">покрытие базы {pct(item.baseline_coverage)}</span>
            </button>
          ))}
        </div>
      </Band>
    </Page>
  )
}
