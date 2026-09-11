/** Обзор: состояние сети одним экраном. */

import { Link } from 'react-router-dom'
import { useMemo } from 'react'
import { useData } from '../lib/store'
import { Page, Band } from '../ui/Page'
import { Panel, Chip, StatusTag, Empty } from '../ui/primitives'
import { Icon } from '../ui/Icon'
import { AiBrief } from '../ui/AiBrief'
import { StatTile } from '../charts/StatTile'
import { RankedBars, PlanMeter } from '../charts/bars'
import { Donut } from '../charts/shapes'
import { ChartBox } from '../charts/kit'
import { PaceChart } from '../charts/shapes'
import { clusterColor, clusterMark, STATUS_META, REC_META } from '../lib/palette'
import { ClusterMark } from '../charts/kit'
import { compact, dec, delta, money, num, pct, plural } from '../lib/format'

const STATUS_ICON = { good: 'check', warn: 'alert', crit: 'alert', serious: 'alert', none: 'minus' } as const

export function Overview() {
  const { data, derived } = useData()
  const { overview, clusters, validation, recommendations, plan, organizations } = data

  const formats = overview.dynamics.find((row) => row.key === 'formats')!

  /* Накопленный темп сети по мероприятиям: факт за девять месяцев, продолжение
     текущим темпом и темп, необходимый для выхода на цель года. */
  const pace = useMemo(() => {
    const fact = formats.fact_ytd
    const runRate = formats.run_rate_year
    const target = formats.target_2026 ?? runRate
    return {
      fact: Array.from({ length: 10 }, (_, month) => [month, (fact / 9) * month] as [number, number]),
      forecast: [[9, fact], [12, runRate]] as Array<[number, number]>,
      required: [[9, fact], [12, target]] as Array<[number, number]>,
      target,
    }
  }, [formats])

  /* «Опережение» и «в графике» — один и тот же статус для кольца: два соседних
     сектора одного цвета читались бы как один. В списке под кольцом они
     по-прежнему разделены. */
  const count = (key: string) => overview.plan_status[key] ?? 0
  const donutParts = [
    { key: 'ok', label: 'Выходят на цель', value: count('опережение') + count('в графике'), color: 'var(--st-good)' },
    { key: 'риск', label: 'Риск', value: count('риск'), color: 'var(--st-warn)' },
    { key: 'срыв', label: 'Срыв', value: count('срыв'), color: 'var(--st-crit)' },
    { key: 'без базы', label: 'Без базы', value: count('без базы'), color: 'var(--st-none)' },
  ].filter((part) => part.value > 0)

  const statusRows = ['опережение', 'в графике', 'риск', 'срыв', 'без базы']
    .filter((key) => count(key) > 0)
    .map((key) => ({ key, label: STATUS_META[key].label, value: count(key), color: STATUS_META[key].color }))

  const atRisk = plan
    .filter((row) => row.status === 'риск' || row.status === 'срыв')
    .sort((a, b) => (a.completion ?? 0) - (b.completion ?? 0))

  const topRecs = [...recommendations].sort((a, b) => b.priority - a.priority).slice(0, 6)

  const impact = overview.recommendations.impact_verified

  return (
    <Page
      eyebrow="Обзор · 9 месяцев 2026 года"
      title="Сеть центров прототипирования"
      lede={
        <>
          Двадцать центров при вузах культуры сведены в один контур: динамика показателей,
          пять устойчивых аудиторных моделей и адресные рекомендации по программированию.
          Источник — годовые формы отчётности, конвейер пересобирается за {dec(overview.build_seconds)} с.
        </>
      }
      actions={
        <Link
          to="/recommendations"
          className="inline-flex items-center gap-1.5 rounded-sm bg-ink px-3 py-[7px] text-[12.5px] font-medium text-ink-inv transition-opacity hover:opacity-88"
        >
          {overview.recommendations.total} {plural(overview.recommendations.total, ['рекомендация', 'рекомендации', 'рекомендаций'])}
          <Icon name="arrow-right" size={13} />
        </Link>
      }
    >
      {/* ── передовица ───────────────────────────────────────────────────── */}
      <div className="panel rise grid grid-cols-1 gap-0 overflow-hidden shadow-card lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)]">
        <div className="flex flex-col justify-between gap-6 px-5 py-6 sm:px-7 lg:border-r lg:border-rule">
          <div>
            <div className="eyebrow">Через центры прошло</div>
            <div className="mt-2.5 flex flex-wrap items-baseline gap-x-3">
              <span className="figure text-[52px] leading-[0.95] text-ink sm:text-[64px]">{num(overview.audience_total)}</span>
              <span className="text-[15px] text-ink-2">
                {plural(overview.audience_total, ['участник', 'участника', 'участников'])}
              </span>
            </div>
            <p className="mt-3 max-w-[46ch] text-[13.5px] leading-relaxed text-ink-2">
              За девять отчётных месяцев 2026 года. Из них {num(overview.residents_total)}{' '}
              стали резидентами центров, а на выходе — {num(overview.products_total)}{' '}
              {plural(overview.products_total, ['творческая работа', 'творческие работы', 'творческих работ'])}.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-rule pt-4">
            <StatusTag
              label={`${overview.plan_at_risk} ${plural(overview.plan_at_risk, ['центр', 'центра', 'центров'])} в зоне риска по годовому плану`}
              color="var(--st-warn)"
              icon="alert"
            />
            <StatusTag
              label={`${clusters.k} аудиторные модели, разбиение признано устойчивым`}
              color="var(--st-good)"
              icon="check"
            />
          </div>
        </div>

        <div className="grid grid-cols-2 divide-x divide-y divide-rule">
          {[
            { label: 'Мероприятий проведено', value: num(overview.formats_total), unit: 'ед.', sub: `цель года — ${num(formats.target_2026)}` },
            { label: 'Творческих продуктов', value: num(overview.products_total), unit: 'раб.', sub: `${dec(overview.median_product_rate * 100, 1)} на 100 участников (медиана)` },
            { label: 'Платные услуги', value: compact(overview.revenue_total), unit: '₽', sub: `прогноз года — ${money(overview.dynamics.find((d) => d.key === 'revenue')!.run_rate_year)}` },
            { label: 'Публикации и федеральные события', value: num(overview.publications_total + overview.federal_events_total), unit: 'шт.', sub: `${num(overview.federal_events_total)} — федеральный уровень` },
          ].map((tile) => (
            <StatTile key={tile.label} {...tile} className="border-0" />
          ))}
        </div>
      </div>

      {/* ── динамика и план ──────────────────────────────────────────────── */}
      <Band
        title="Динамика и исполнение года"
        note="Отчётный факт накоплен за 9 из 12 месяцев — прогноз считается по текущему темпу"
      >
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
          <Panel
            eyebrow="Мероприятия · накопленным итогом"
            title="Темп сети выводит на цель года"
            subtitle={
              <>
                Факт {num(formats.fact_ytd)} мероприятий за девять месяцев. Сохранение темпа даёт{' '}
                {num(formats.run_rate_year)} к декабрю при цели {num(formats.target_2026)}.
              </>
            }
            footnote={
              <>
                База 2025 года заполнена у {formats.baseline_orgs} из {overview.organizations} центров
                ({pct(formats.baseline_coverage)}), поэтому темп считается по сопоставимому кругу:
                {' '}{delta(formats.growth_year)} в годовом выражении.
              </>
            }
          >
            <ChartBox height={230}>
              {({ width, height }) => (
                <PaceChart
                  width={width}
                  height={height}
                  formatValue={(value) => num(Math.round(value))}
                  target={{ value: pace.target, label: `цель ${num(pace.target)}` }}
                  series={[
                    { id: 'fact', label: 'Факт', color: 'var(--ink)', points: pace.fact },
                    { id: 'forecast', label: 'Текущий темп', color: 'var(--c-0)', points: pace.forecast, dashed: true },
                    { id: 'required', label: 'Нужный темп', color: 'var(--ink-3)', points: pace.required, dashed: true, width: 1.5 },
                  ]}
                />
              )}
            </ChartBox>
            <ul className="mt-2 flex flex-wrap items-center gap-x-5 gap-y-1.5 text-[11.5px] text-ink-2">
              <li className="flex items-center gap-1.5"><span className="h-[2px] w-5 rounded-full bg-ink" />Факт, 9 месяцев</li>
              <li className="flex items-center gap-1.5"><span className="h-[2px] w-5 rounded-full" style={{ background: 'var(--c-0)', maskImage: 'repeating-linear-gradient(90deg,#000 0 5px,transparent 5px 9px)' }} />Продолжение текущим темпом</li>
              <li className="flex items-center gap-1.5">
              <span className="h-[2px] w-5" style={{ background: 'var(--ink-3)', maskImage: 'repeating-linear-gradient(90deg,#000 0 5px,transparent 5px 9px)' }} />
              Темп, нужный для цели
            </li>
            </ul>
          </Panel>

          <Panel
            eyebrow="Годовой план"
            title="Кто выходит на цель, а кто нет"
            subtitle="Статус считается по разрыву между текущим темпом и целью на декабрь"
            footnote={
              <Link to="/dynamics" className="inline-flex items-center gap-1 text-ink-2 underline decoration-rule-2 underline-offset-2 hover:text-ink">
                Разбор по каждому центру <Icon name="arrow-right" size={12} />
              </Link>
            }
          >
            <div className="flex flex-wrap items-start gap-5">
              <Donut
                parts={donutParts}
                size={138}
                thickness={17}
                centerValue={num(overview.organizations)}
                centerLabel="центров"
              />
              <ul className="min-w-[150px] flex-1 space-y-1.5">
                {statusRows.map((part) => (
                  <li key={part.key} className="flex items-center justify-between gap-3 text-[12.5px]">
                    <StatusTag
                      label={part.label}
                      color={part.color}
                      icon={STATUS_ICON[STATUS_META[part.key]?.tone ?? 'none']}
                    />
                    <span className="tnum font-medium text-ink">{part.value}</span>
                  </li>
                ))}
              </ul>
            </div>

            {atRisk.length > 0 && (
              <div className="mt-4 border-t border-rule pt-3">
                <div className="eyebrow mb-2">Наибольшее отставание</div>
                <ul className="space-y-2">
                  {atRisk.slice(0, 4).map((row) => (
                    <li key={row.org_id}>
                      <div className="mb-1 flex items-baseline justify-between gap-3">
                        <span className="truncate text-[12.5px] text-ink-2">{row.short_name}</span>
                        <span className="tnum shrink-0 text-[12px] font-medium text-ink">{pct(row.completion)}</span>
                      </div>
                      <PlanMeter
                        completion={row.completion ?? 0}
                        forecastShare={row.target_2026 ? (row.run_rate_forecast ?? 0) / row.target_2026 : null}
                        color={STATUS_META[row.status]?.color ?? 'var(--st-none)'}
                        height={6}
                      />
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </Panel>
        </div>
      </Band>

      {/* ── резюме модели ────────────────────────────────────────────────── */}
      <Band title="Исполнительское резюме" note="Собирается языковой моделью по рассчитанным показателям">
        <AiBrief
          facts={[
            { label: 'Участников за 9 месяцев', value: num(overview.audience_total) },
            { label: 'Мероприятий · цель года', value: `${num(overview.formats_total)} · ${num(formats.target_2026)}` },
            { label: 'Творческих продуктов', value: num(overview.products_total) },
            { label: 'Платные услуги', value: money(overview.revenue_total) },
            { label: 'Центров в зоне риска', value: `${overview.plan_at_risk} из ${overview.organizations}` },
            { label: 'Подтверждённый резерв выручки', value: money(impact.revenue?.total ?? 0) },
          ]}
        />
      </Band>

      {/* ── кластеры ─────────────────────────────────────────────────────── */}
      <Band
        title="Аудиторные модели"
        note={validation.clustering.verdict}
      >
        <div className="stagger grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-5">
          {clusters.profiles.map((profile) => (
            <Link
              key={profile.cluster_id}
              to="/clusters"
              className="panel group flex flex-col gap-3 p-4 shadow-card transition-[border-color,transform] duration-150 hover:-translate-y-0.5 hover:border-rule-strong"
            >
              <div className="flex items-start justify-between gap-2">
                <svg width={16} height={16} viewBox="-8 -8 16 16" aria-hidden>
                  <ClusterMark shape={clusterMark(profile.cluster_id)} x={0} y={0} r={5.5} fill={clusterColor(profile.cluster_id)} strokeWidth={0} />
                </svg>
                <span className="tnum text-[11px] text-ink-3">
                  {profile.size} {plural(profile.size, ['центр', 'центра', 'центров'])}
                </span>
              </div>
              <div>
                <h3 className="text-[13.5px] leading-snug font-medium text-ink">{profile.name}</h3>
                <p className="mt-1 text-[11.5px] leading-snug text-ink-3">{profile.summary}</p>
              </div>
              <div className="mt-auto flex flex-wrap gap-1">
                {profile.member_names.slice(0, 3).map((name) => (
                  <Chip key={name}>{name}</Chip>
                ))}
                {profile.size > 3 && <Chip>+{profile.size - 3}</Chip>}
              </div>
            </Link>
          ))}
        </div>
      </Band>

      {/* ── рекомендации ─────────────────────────────────────────────────── */}
      <Band
        title="Что делать дальше"
        note={`Средний приоритет ${dec(overview.recommendations.mean_priority, 0)} из 100`}
      >
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
          <Panel
            eyebrow="Первая очередь"
            title="Шесть рекомендаций с наибольшим приоритетом"
            subtitle="Приоритет складывается из размера резерва, надёжности данных и доли аудитории, которую затрагивает мера"
            footnote={
              <Link to="/recommendations" className="inline-flex items-center gap-1 text-ink-2 underline decoration-rule-2 underline-offset-2 hover:text-ink">
                Все {overview.recommendations.total} рекомендаций <Icon name="arrow-right" size={12} />
              </Link>
            }
          >
            <ul className="divide-y divide-rule">
              {topRecs.map((rec, index) => (
                <li key={`${rec.org_id}-${rec.rec_type}-${index}`} className="flex gap-3 py-2.5 first:pt-0 last:pb-0">
                  <span className="eyebrow mt-[3px] w-6 shrink-0 tabular-nums">{rec.priority}</span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                      <span className="text-[13px] font-medium text-ink">{rec.title}</span>
                      <span className="text-[11.5px] text-ink-3">· {derived.nameOf(rec.org_id)}</span>
                    </div>
                    <p className="mt-0.5 line-clamp-2 text-[12px] leading-snug text-ink-2">{rec.action}</p>
                  </div>
                  {rec.impact_value != null && (
                    <span className="tnum w-[96px] shrink-0 self-center text-right text-[12px] whitespace-nowrap text-ink-2">
                      +{rec.impact_unit === '₽' ? money(rec.impact_value) : `${compact(rec.impact_value)} ${rec.impact_unit ?? ''}`}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </Panel>

          <Panel
            eyebrow="Совокупный резерв"
            title="Если закрыть разрыв с медианой своей модели"
            subtitle="Показан подтверждённый резерв — без центров, у которых отчёт внутренне противоречив"
            footnote={
              `Из подтверждённого резерва исключено ${overview.recommendations.flagged} ` +
              `${plural(overview.recommendations.flagged, ['мера', 'меры', 'мер'])} по ` +
              `${overview.recommendations.flagged_orgs.length} ${plural(overview.recommendations.flagged_orgs.length, ['центру', 'центрам', 'центрам'])} ` +
              'с расхождениями в отчётности'
            }
          >
            <ul className="space-y-3">
              {[
                ['participants', 'Участники', 'чел.'],
                ['products', 'Творческие продукты', 'шт.'],
                ['revenue', 'Платные услуги', '₽'],
                ['publications', 'Публикации', 'шт.'],
                ['formats', 'Мероприятия', 'шт.'],
              ].map(([key, label, unit]) => {
                const entry = impact[key]
                if (!entry) return null
                const full = overview.recommendations.impact[key]
                return (
                  <li key={key}>
                    <div className="flex items-baseline justify-between gap-3">
                      <span className="text-[12.5px] text-ink-2">{label}</span>
                      <span className="tnum text-[13px] font-medium text-ink">
                        +{unit === '₽' ? money(entry.total) : `${compact(entry.total)} ${unit}`}
                      </span>
                    </div>
                    <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-panel-2">
                      <div
                        className="bar-grow h-full rounded-full bg-ink-2"
                        style={{ width: `${full?.total ? (entry.total / full.total) * 100 : 100}%` }}
                      />
                    </div>
                    <div className="mt-0.5 text-[10.5px] text-ink-3">
                      {entry.count} {plural(entry.count, ['центр', 'центра', 'центров'])} · из заявленных
                      {' '}{unit === '₽' ? money(full?.total ?? 0) : compact(full?.total ?? 0)}
                    </div>
                  </li>
                )
              })}
            </ul>
          </Panel>
        </div>
      </Band>

      {/* ── распределение по типам и качество ────────────────────────────── */}
      <Band title="Структура рекомендаций и качество исходных данных">
        <div className="grid items-start grid-cols-1 gap-4 xl:grid-cols-2">
          <Panel eyebrow="Типы мер" title="Чего сеть недобирает чаще всего">
            {Object.keys(overview.recommendations.by_type).length === 0 ? (
              <Empty text="Рекомендаций нет" />
            ) : (
              <RankedBars
                labelWidth={150}
                valueWidth={30}
                format={(value) => num(value)}
                items={Object.entries(overview.recommendations.by_type)
                  .sort((a, b) => b[1] - a[1])
                  .map(([type, count]) => ({
                    id: type,
                    label: REC_META[type]?.short ?? type,
                    value: count,
                    color: 'var(--ink-2)',
                    tip: <><strong className="text-ink">{REC_META[type]?.label ?? type}</strong></>,
                  }))}
              />
            )}
          </Panel>

          <Panel
            eyebrow="Контроль качества"
            title="Что в отчётах не сходится"
            subtitle="Разбор ведётся до рекомендаций: центр с противоречивым отчётом не попадает в подтверждённый резерв"
            footnote={
              <Link to="/quality" className="inline-flex items-center gap-1 text-ink-2 underline decoration-rule-2 underline-offset-2 hover:text-ink">
                Полный отчёт контроля <Icon name="arrow-right" size={12} />
              </Link>
            }
          >
            <StatRowInline
              items={[
                { label: 'Аномалий в показателях', value: num(overview.anomalies) },
                { label: 'Правок при разборе файлов', value: num(Object.values(overview.data_quality).reduce((sum, value) => sum + value, 0)) },
                { label: 'Заполненность ячеек', value: pct(data.quality.cell_coverage) },
                { label: 'Организаций с пометками', value: num(new Set(data.anomalies.map((a) => a.org_id)).size) },
              ]}
            />
            <ul className="mt-3 space-y-2 border-t border-rule pt-3">
              {data.anomalies.slice(0, 3).map((anomaly, index) => (
                <li key={index} className="flex gap-2.5">
                  <span className="mt-[3px] shrink-0" style={{ color: anomaly.severity === 'error' ? 'var(--st-crit)' : 'var(--st-warn)' }}>
                    <Icon name="alert" size={12} strokeWidth={2} />
                  </span>
                  <p className="text-[12px] leading-snug text-ink-2">
                    <span className="font-medium text-ink">{derived.nameOf(anomaly.org_id)}.</span>{' '}
                    {anomaly.message}
                  </p>
                </li>
              ))}
            </ul>
          </Panel>
        </div>
      </Band>

      <p className="mt-8 max-w-[80ch] border-t border-rule pt-4 text-[11.5px] leading-relaxed text-ink-3">
        Источник данных — {organizations.length} файлов годовой отчётности (формы 1 и 2 с приложениями).
        Показатели приводятся к единым единицам на этапе разбора, все правки фиксируются в отчёте контроля качества.
        Разбиение на модели проверено перестановочным тестом и исключением по одному; рекомендации — повторной
        сборкой на возмущённых данных.
      </p>
    </Page>
  )
}

function StatRowInline({ items }: { items: Array<{ label: string; value: string }> }) {
  return (
    <dl className="grid grid-cols-2 gap-x-5 gap-y-2.5">
      {items.map((item) => (
        <div key={item.label}>
          <dt className="text-[11.5px] leading-snug text-ink-3">{item.label}</dt>
          <dd className="tnum mt-0.5 text-[17px] font-semibold text-ink">{item.value}</dd>
        </div>
      ))}
    </dl>
  )
}
