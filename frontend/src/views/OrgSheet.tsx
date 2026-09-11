/** Карточка центра: паспорт, модель, показатели против сети, меры и пометки. */

import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { useData } from '../lib/store'
import type { OrgDetail } from '../lib/types'
import { Sheet, Chip, StatusTag, Skeleton, Empty, Button } from '../ui/primitives'
import { Icon } from '../ui/Icon'
import { AiBrief } from '../ui/AiBrief'
import { ShareBar, PlanMeter } from '../charts/bars'
import { StripPlot } from '../charts/shapes'
import { ClusterMark } from '../charts/kit'
import { channelColor, clusterColor, clusterMark, STATUS_META, SEVERITY_META } from '../lib/palette'
import { compact, dec, money, num, pct, plural, withUnit } from '../lib/format'
import { RecCard } from './RecCard'

const STATUS_ICON = { good: 'check', warn: 'alert', crit: 'alert', serious: 'alert', none: 'minus' } as const

/** Показатели, по которым центр сравнивается с сетью. */
const BENCHMARKS: Array<{ key: string; label: string; format: (value: number) => string; hint: string }> = [
  { key: 'audience_total', label: 'Аудитория', format: (v) => `${num(v)} чел.`, hint: 'Сколько человек прошло через центр за отчётный период' },
  { key: 'audience_per_format', label: 'Участников на мероприятие', format: (v) => dec(v, 1), hint: 'Наполняемость: аудитория, делённая на число проведённых форматов' },
  { key: 'product_rate', label: 'Продуктов на участника', format: (v) => dec(v, 2), hint: 'Сколько творческих работ выходит на одного участника' },
  { key: 'resident_rate', label: 'Доля резидентов', format: (v) => pct(v), hint: 'Какая часть аудитории закрепилась в центре' },
  { key: 'revenue_per_participant', label: 'Выручка на участника', format: (v) => money(v), hint: 'Платные услуги, делённые на аудиторию' },
  { key: 'publicity_per_format', label: 'Публичность на мероприятие', format: (v) => dec(v, 2), hint: 'Публикации и федеральные события на один формат' },
]

export function OrgSheet({ orgId, onClose }: { orgId: string | null; onClose: () => void }) {
  const { data, derived } = useData()
  const [detail, setDetail] = useState<OrgDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [tab, setTab] = useState<'profile' | 'recs' | 'brief'>('profile')

  useEffect(() => {
    if (!orgId) return
    setDetail(null)
    setError(null)
    setTab('profile')
    let alive = true
    api.organization(orgId)
      .then((value) => { if (alive) setDetail(value) })
      .catch((failure: Error) => { if (alive) setError(failure.message) })
    return () => { alive = false }
  }, [orgId])

  if (!orgId) return null

  const org = derived.byId.get(orgId)
  const recs = derived.recsByOrg.get(orgId) ?? []
  const anomalies = derived.anomaliesByOrg.get(orgId) ?? []
  const meta = org ? STATUS_META[org.status] : undefined

  return (
    <Sheet open onClose={onClose} label={`Карточка центра ${org?.short_name ?? ''}`}>
      <header className="shrink-0 border-b border-rule bg-panel px-5 py-4 sm:px-7">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="eyebrow flex items-center gap-2">
              {org && (
                <svg width={11} height={11} viewBox="-6 -6 12 12" aria-hidden>
                  <ClusterMark shape={clusterMark(org.cluster)} x={0} y={0} r={4.5} fill={clusterColor(org.cluster)} strokeWidth={0} />
                </svg>
              )}
              {detail?.cluster.name ?? derived.clusterById.get(org?.cluster ?? 0)?.name ?? 'Центр'}
            </div>
            <h2 className="mt-1.5 font-serif text-[24px] leading-tight font-semibold tracking-[-0.02em] text-ink">
              {org?.short_name ?? orgId}
            </h2>
            <p className="mt-1 text-[12.5px] leading-snug text-ink-2">{org?.full_name}</p>
            <div className="mt-2.5 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-[11.5px] text-ink-3">
              {org?.center && <span>{org.center}</span>}
              {org?.report_date && <span>отчёт от {org.report_date}</span>}
              {org?.source_file && <span className="font-mono">{org.source_file}</span>}
            </div>
          </div>
          <Button icon="close" onClick={onClose} title="Закрыть (Esc)" />
        </div>

        <nav className="mt-4 flex gap-0.5" role="tablist" aria-label="Разделы карточки">
          {([
            ['profile', 'Профиль'],
            ['recs', `Меры${recs.length ? ` · ${recs.length}` : ''}`],
            ['brief', 'Разбор модели'],
          ] as const).map(([key, label]) => (
            <button
              key={key}
              role="tab"
              aria-selected={tab === key}
              onClick={() => setTab(key)}
              className={`relative px-3 py-2 text-[12.5px] font-medium transition-colors ${
                tab === key ? 'text-ink' : 'text-ink-3 hover:text-ink-2'
              }`}
            >
              {label}
              {tab === key && <span className="absolute right-2 bottom-0 left-2 h-[2px] rounded-full bg-ink" />}
            </button>
          ))}
        </nav>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5 sm:px-7">
        {error && <Empty text={`Карточка не загрузилась: ${error}`} />}
        {!detail && !error && (
          <div className="space-y-3">
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-40 w-full" />
          </div>
        )}

        {detail && org && tab === 'profile' && (
          <div className="space-y-6">
            {/* ключевые числа */}
            <div className="panel grid grid-cols-2 divide-x divide-y divide-rule overflow-hidden sm:grid-cols-4 sm:divide-y-0">
              {[
                ['Аудитория', `${num(org.audience_total)}`, 'чел.'],
                ['Мероприятий', `${num(org.supply_total)}`, 'ед.'],
                ['Творческих работ', `${num(org.products_total)}`, 'шт.'],
                ['Платные услуги', compact(org.revenue_total), '₽'],
              ].map(([label, value, unit]) => (
                <div key={label} className="px-3.5 py-3">
                  <div className="text-[11px] leading-snug text-ink-3">{label}</div>
                  <div className="mt-1 flex items-baseline gap-1">
                    <span className="figure text-[21px] text-ink">{value}</span>
                    <span className="text-[11px] text-ink-3">{unit}</span>
                  </div>
                </div>
              ))}
            </div>

            {/* план */}
            <section>
              <div className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
                <h3 className="text-[13.5px] font-medium text-ink">Годовой план</h3>
                {meta && <StatusTag label={meta.label} color={meta.color} icon={STATUS_ICON[meta.tone]} />}
              </div>
              {org.completion == null ? (
                <Empty text="Базы 2025 года нет — цель на год не рассчитывается" />
              ) : (
                <>
                  <PlanMeter
                    completion={org.completion}
                    forecastShare={org.target_2026 ? (org.run_rate_forecast ?? 0) / org.target_2026 : null}
                    color={meta?.color ?? 'var(--st-none)'}
                    height={10}
                  />
                  <dl className="mt-2.5 grid grid-cols-2 gap-x-5 gap-y-2 sm:grid-cols-4">
                    {[
                      ['Исполнение', pct(org.completion)],
                      ['Факт / цель', `${num(detail.plan.fact_ytd)} / ${dec(org.target_2026 ?? 0)}`],
                      ['Прогноз года', dec(org.run_rate_forecast ?? 0)],
                      ['Темп сейчас / нужный', `${dec(detail.plan.current_monthly_rate ?? 0, 1)} / ${dec(detail.plan.required_monthly_rate ?? 0, 1)}`],
                    ].map(([label, value]) => (
                      <div key={label}>
                        <dt className="text-[10.5px] leading-snug text-ink-3">{label}</dt>
                        <dd className="tnum mt-0.5 text-[13px] font-medium text-ink">{value}</dd>
                      </div>
                    ))}
                  </dl>
                  <p className="mt-1.5 text-[11px] text-ink-3">{meta?.hint}</p>
                </>
              )}
            </section>

            {/* состав аудитории */}
            <section>
              <h3 className="mb-2 text-[13.5px] font-medium text-ink">Из чего складывается аудитория</h3>
              <ShareBar
                height={18}
                parts={data.meta.channels.map((channel, index) => ({
                  key: channel.key,
                  label: channel.label,
                  value: Number(org[`audience_${channel.key}`] ?? 0),
                  color: channelColor(index),
                }))}
              />
              <ul className="mt-2.5 grid grid-cols-2 gap-x-5 gap-y-1.5 sm:grid-cols-4">
                {data.meta.channels.map((channel, index) => {
                  const value = Number(org[`audience_${channel.key}`] ?? 0)
                  const products = Number(org[`products_${channel.key}`] ?? 0)
                  return (
                    <li key={channel.key} className="text-[11.5px]">
                      <div className="flex items-center gap-1.5">
                        <span className="size-2.5 shrink-0 rounded-[2px]" style={{ background: channelColor(index) }} />
                        <span className="truncate text-ink-2">{channel.label}</span>
                      </div>
                      <div className="tnum mt-0.5 ml-4 text-ink">
                        {num(value)} чел.
                        <span className="text-ink-3"> · {num(products)} раб.</span>
                      </div>
                    </li>
                  )
                })}
              </ul>
            </section>

            {/* сравнение с сетью */}
            <section>
              <h3 className="mb-1 text-[13.5px] font-medium text-ink">Положение в сети</h3>
              <p className="mb-3 text-[11.5px] leading-snug text-ink-3">
                Каждая полоса — распределение показателя по двадцати центрам. Серая зона — где лежит половина сети,
                выделенная точка — этот центр.
              </p>
              <ul className="space-y-3.5">
                {BENCHMARKS.map((benchmark) => {
                  const series = data.organizations.map((item) => ({
                    id: item.org_id,
                    label: item.short_name,
                    value: Number(item[benchmark.key] ?? 0),
                    color: item.org_id === orgId ? clusterColor(item.cluster) : 'var(--ink-3)',
                  }))
                  const sorted = [...series].map((item) => item.value).sort((a, b) => a - b)
                  const q = (p: number) => sorted[Math.min(sorted.length - 1, Math.floor(p * (sorted.length - 1)))]
                  const own = Number(org[benchmark.key] ?? 0)
                  const rank = sorted.filter((value) => value > own).length + 1
                  return (
                    <li key={benchmark.key}>
                      <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                        <span className="text-[12px] text-ink-2" title={benchmark.hint}>{benchmark.label}</span>
                        <span className="tnum text-[12px] text-ink">
                          <span className="font-medium">{benchmark.format(own)}</span>
                          <span className="text-ink-3"> · {rank}-е место из {series.length}</span>
                        </span>
                      </div>
                      <StripPlot
                        items={series}
                        median={q(0.5)}
                        p25={q(0.25)}
                        p75={q(0.75)}
                        format={benchmark.format}
                        highlight={orgId}
                        height={56}
                      />
                    </li>
                  )
                })}
              </ul>
            </section>

            {/* модель */}
            <section>
              <h3 className="mb-2 text-[13.5px] font-medium text-ink">Аудиторная модель</h3>
              <div className="panel p-4">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <span className="text-[13px] font-medium text-ink">{detail.cluster.name}</span>
                  <span className="text-[11.5px] text-ink-3">
                    уверенность {pct(detail.cluster.membership_confidence ?? 1)} · силуэт {dec(detail.cluster.silhouette, 2)}
                  </span>
                </div>
                <p className="mt-1 text-[12px] leading-snug text-ink-2">{detail.cluster.summary}</p>
                <div className="mt-3 border-t border-rule pt-2.5">
                  <div className="eyebrow mb-1.5">Сопоставимые центры</div>
                  <div className="flex flex-wrap gap-1.5">
                    {detail.cluster.peers.map((peer) => (
                      <Chip key={peer}>{derived.nameOf(peer)}</Chip>
                    ))}
                  </div>
                </div>
              </div>
            </section>

            {/* пометки */}
            {anomalies.length > 0 && (
              <section>
                <h3 className="mb-2 text-[13.5px] font-medium text-ink">Что не сходится в отчёте</h3>
                <ul className="space-y-2">
                  {anomalies.map((anomaly, index) => (
                    <li key={index} className="panel flex gap-2.5 p-3">
                      <span className="mt-[2px] shrink-0" style={{ color: SEVERITY_META[anomaly.severity].color }}>
                        <Icon name="alert" size={13} strokeWidth={2} />
                      </span>
                      <div className="min-w-0">
                        <div className="font-mono text-[10.5px] text-ink-3">{anomaly.metric} · {SEVERITY_META[anomaly.severity].label}</div>
                        <p className="mt-0.5 text-[12px] leading-snug text-ink-2">{anomaly.message}</p>
                      </div>
                    </li>
                  ))}
                </ul>
              </section>
            )}
          </div>
        )}

        {detail && tab === 'recs' && (
          recs.length === 0 ? (
            <Empty text="Для этого центра рекомендаций нет: по всем показателям он не ниже медианы своей модели" />
          ) : (
            <ul className="space-y-3">
              {[...recs].sort((a, b) => b.priority - a.priority).map((rec, index) => (
                <li key={`${rec.rec_type}-${rec.channel}-${index}`}>
                  <RecCard rec={rec} showOrg={false} />
                </li>
              ))}
            </ul>
          )
        )}

        {detail && tab === 'brief' && (
          <AiBrief
            orgId={orgId}
            title={`Разбор центра «${org?.short_name}»`}
            facts={[
              { label: 'Аудитория', value: `${num(org?.audience_total ?? 0)} чел.` },
              { label: 'Мероприятий', value: num(org?.supply_total ?? 0) },
              { label: 'Модель', value: detail.cluster.name },
              { label: 'Статус плана', value: meta?.label ?? '—' },
              { label: 'Мер в очереди', value: `${recs.length} ${plural(recs.length, ['мера', 'меры', 'мер'])}` },
            ]}
          />
        )}
      </div>

      {org && (
        <footer className="shrink-0 border-t border-rule bg-panel-2 px-5 py-2.5 text-[11px] text-ink-3 sm:px-7">
          Все показатели — из формы отчётности {org.year} года
          {org.ip_total > 0 ? ` · объектов интеллектуальной собственности: ${num(org.ip_total)}` : ''}
          {' · '}наполняемость {dec(org.audience_per_format, 1)} чел. на мероприятие
          {' · '}выручка на участника {withUnit(org.revenue_per_participant, '₽')}
        </footer>
      )}
    </Sheet>
  )
}
